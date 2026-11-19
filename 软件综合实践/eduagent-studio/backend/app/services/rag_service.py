import re
import zipfile
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.db.repositories import ResourceTaskRepository
from app.models.rag import RAGChunk, RAGDocument
from app.schemas.rag import RAGUploadRequest
from app.services.ai_client import AIClient, AIServiceError, OpenAICompatibleAIClient


SUPPORTED_TEXT_SUFFIXES = {".txt", ".md", ".markdown"}
SUPPORTED_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff"}
SUPPORTED_UPLOAD_SUFFIXES = SUPPORTED_TEXT_SUFFIXES | SUPPORTED_IMAGE_SUFFIXES | {".docx", ".pdf"}
MAX_RAG_CHUNK_CHARS = 500
ORIGINAL_FILE_DIR = Path(__file__).resolve().parents[2] / ".data" / "rag_files"


class RAGService:
    def __init__(
        self,
        repository: ResourceTaskRepository,
        ai_client: AIClient | None = None,
    ):
        self._repository = repository
        self._ai_client = ai_client or OpenAICompatibleAIClient()

    async def upload(self, request: RAGUploadRequest) -> dict[str, Any]:
        document_id = str(uuid4())
        now = datetime.now(UTC)
        notebook_id = request.notebook_id or request.course_id
        document = RAGDocument(
            document_id=document_id,
            source_id=document_id,
            user_id=request.user_id,
            course_id=request.course_id,
            notebook_id=notebook_id,
            filename=request.filename,
            source_title=request.filename,
            source_content=request.content,
            content_type=request.content_type,
            source_type=request.source_type,
            upload_status="processing",
            chunk_count=0,
            metadata={**request.metadata, "upload_mode": request.metadata.get("upload_mode", "text")},
            created_at=now,
            updated_at=now,
        )
        await self._repository.save_rag_document(document)

        try:
            chunks = await self._index_document(document, request.content)
        except Exception as exc:
            await self._mark_document_failed(document, exc)
            raise

        return self.format_upload_result(document, chunks)

    async def create_file_source(
        self,
        *,
        user_id: str,
        course_id: str,
        notebook_id: str | None = None,
        filename: str,
        content_type: str,
        content_size: int,
        source_type: str = "course_material",
        metadata: dict[str, str] | None = None,
    ) -> RAGDocument:
        _ensure_supported_upload(filename, content_type)

        document_id = str(uuid4())
        now = datetime.now(UTC)
        effective_content_type = content_type or "application/octet-stream"
        effective_source_type = _resolve_source_type(filename, effective_content_type, source_type)
        document = RAGDocument(
            document_id=document_id,
            source_id=document_id,
            user_id=user_id,
            course_id=course_id,
            notebook_id=notebook_id or course_id,
            filename=filename,
            source_title=filename,
            source_content="",
            content_type=effective_content_type,
            source_type=effective_source_type,
            upload_status="processing",
            chunk_count=0,
            metadata={
                "upload_mode": "file",
                "size_bytes": str(content_size),
                "file_kind": _file_kind(filename, effective_content_type),
                **(metadata or {}),
            },
            created_at=now,
            updated_at=now,
        )
        await self._repository.save_rag_document(document)
        return document

    async def process_file_source(
        self,
        document: RAGDocument,
        content: bytes,
        *,
        raise_errors: bool = False,
    ) -> list[RAGChunk]:
        try:
            text = _extract_upload_text(document.filename, document.content_type, content)
            return await self._index_document(document, text)
        except Exception as exc:
            await self._mark_document_failed(document, exc)
            if raise_errors:
                raise
            return []

    async def save_original_pdf_file(
        self,
        document: RAGDocument,
        content: bytes,
    ) -> RAGDocument:
        if _file_suffix(document.filename) != ".pdf":
            return document

        ORIGINAL_FILE_DIR.mkdir(parents=True, exist_ok=True)
        path = ORIGINAL_FILE_DIR / f"{document.document_id}.pdf"
        path.write_bytes(content)
        file_url = f"/api/rag/documents/{document.document_id}/file"
        document.metadata = {
            **document.metadata,
            "original_file_url": file_url,
            "preview_url": file_url,
            "preview_type": "pdf",
            "original_type": "pdf",
        }
        document.updated_at = datetime.now(UTC)
        await self._repository.save_rag_document(document)
        return document

    async def upload_file(
        self,
        *,
        user_id: str,
        course_id: str,
        notebook_id: str | None = None,
        filename: str,
        content_type: str,
        content: bytes,
        source_type: str = "course_material",
    ) -> dict[str, Any]:
        document = await self.create_file_source(
            user_id=user_id,
            course_id=course_id,
            notebook_id=notebook_id,
            filename=filename,
            content_type=content_type,
            content_size=len(content),
            source_type=source_type,
        )
        chunks = await self.process_file_source(document, content, raise_errors=True)
        return self.format_upload_result(document, chunks)

    async def list_documents(
        self,
        user_id: str | None = None,
        course_id: str | None = None,
        notebook_id: str | None = None,
    ) -> dict[str, Any]:
        documents = await self._repository.list_rag_documents(
            user_id=user_id,
            course_id=course_id,
            notebook_id=notebook_id,
        )
        failed_documents = [
            document for document in documents if document.upload_status == "failed"
        ]
        for document in failed_documents:
            await self._repository.delete_rag_document(document.document_id)
        documents = [
            document for document in documents if document.upload_status != "failed"
        ]
        return {
            "items": [document.model_dump(mode="json") for document in documents],
            "total": len(documents),
        }

    async def delete_document(self, document_id: str) -> bool:
        deleted = await self._repository.delete_rag_document(document_id)
        if deleted:
            self._delete_original_file(document_id)
        return deleted

    async def get_original_file_path(self, document_id: str) -> Path | None:
        document = await self._repository.get_rag_document(document_id)
        if document is None:
            return None

        path = _original_pdf_path(document_id)
        if path is None or not path.is_file():
            return None
        return path

    async def rename_document(
        self,
        document_id: str,
        source_title: str,
    ) -> dict[str, Any] | None:
        title = source_title.strip()
        if not title:
            raise ValueError("source title cannot be empty")

        document = await self._repository.get_rag_document(document_id)
        if document is None:
            return None

        document.source_title = title
        document.updated_at = datetime.now(UTC)
        await self._repository.save_rag_document(document)
        return document.model_dump(mode="json")

    async def _index_document(
        self,
        document: RAGDocument,
        content: str,
    ) -> list[RAGChunk]:
        normalized = _normalize_source_text(content)
        chunk_texts = self._split_chunks(normalized)
        embeddings = await self._ai_client.embed_texts(chunk_texts)
        if len(embeddings) != len(chunk_texts):
            raise AIServiceError("embedding count does not match RAG chunk count")

        chunks = [
            self._make_chunk(
                document_id=document.document_id,
                course_id=document.course_id,
                chunk_index=index,
                text=text,
                embedding=embeddings[index],
            )
            for index, text in enumerate(chunk_texts)
        ]

        await self._repository.save_rag_chunks(chunks)
        document.source_content = normalized
        document.chunk_count = len(chunks)
        document.upload_status = "success"
        document.processing_error = None
        document.updated_at = datetime.now(UTC)
        await self._repository.save_rag_document(document)
        return chunks

    async def _mark_document_failed(
        self,
        document: RAGDocument,
        exc: Exception,
    ) -> None:
        self._delete_original_file(document.document_id)
        await self._repository.delete_rag_document(document.document_id)

    def _delete_original_file(self, document_id: str) -> None:
        path = _original_pdf_path(document_id)
        if path is not None:
            path.unlink(missing_ok=True)

    def _split_chunks(self, content: str) -> list[str]:
        normalized = _normalize_source_text(content)
        paragraphs = [
            paragraph.strip()
            for paragraph in re.split(r"\n\s*\n", normalized)
            if paragraph.strip()
        ]
        if not paragraphs:
            paragraphs = [normalized]

        chunk_texts: list[str] = []
        buffer = ""
        for paragraph in paragraphs:
            for part in _split_long_paragraph(paragraph):
                next_buffer = f"{buffer}\n\n{part}".strip() if buffer else part
                if len(next_buffer) <= MAX_RAG_CHUNK_CHARS:
                    buffer = next_buffer
                    continue

                if buffer:
                    chunk_texts.append(buffer)
                buffer = part

        if buffer:
            chunk_texts.append(buffer)
        return chunk_texts

    def _make_chunk(
        self,
        document_id: str,
        course_id: str,
        chunk_index: int,
        text: str,
        embedding: list[float],
    ) -> RAGChunk:
        return RAGChunk(
            chunk_id=str(uuid4()),
            document_id=document_id,
            course_id=course_id,
            chunk_index=chunk_index,
            text=text,
            embedding=embedding,
        )

    def format_upload_result(
        self,
        document: RAGDocument,
        chunks: list[RAGChunk] | None = None,
    ) -> dict[str, Any]:
        chunks = chunks or []
        return {
            "document_id": document.document_id,
            "source_id": document.source_id,
            "upload_status": document.upload_status,
            "chunk_count": document.chunk_count,
            "document": document.model_dump(mode="json"),
            "chunks": [
                {
                    "chunk_id": chunk.chunk_id,
                    "chunk_index": chunk.chunk_index,
                    "preview": chunk.text[:80],
                }
                for chunk in chunks
            ],
        }


def _extract_upload_text(filename: str, content_type: str, content: bytes) -> str:
    suffix = _file_suffix(filename)
    if suffix in SUPPORTED_TEXT_SUFFIXES:
        text = _decode_text(content)
    elif suffix == ".docx":
        text = _extract_docx_text(content)
    elif suffix == ".pdf":
        text = _extract_pdf_text(content)
    elif suffix in SUPPORTED_IMAGE_SUFFIXES or content_type.startswith("image/"):
        text = _extract_image_text(filename, content)
    else:
        raise ValueError("仅支持图片、PDF、Word 文档、Markdown、TXT 和纯文本文件。")

    return _normalize_source_text(text)


def _ensure_supported_upload(filename: str, content_type: str) -> None:
    suffix = _file_suffix(filename)
    if suffix in SUPPORTED_UPLOAD_SUFFIXES or content_type.startswith("image/"):
        return
    raise ValueError("仅支持图片、PDF、Word 文档、Markdown、TXT 和纯文本文件。")


def _normalize_source_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        raise ValueError("未能从来源中提取可用于检索的文本。")
    return normalized


def _split_long_paragraph(paragraph: str) -> list[str]:
    if len(paragraph) <= MAX_RAG_CHUNK_CHARS:
        return [paragraph]

    return [
        paragraph[start : start + MAX_RAG_CHUNK_CHARS].strip()
        for start in range(0, len(paragraph), MAX_RAG_CHUNK_CHARS)
        if paragraph[start : start + MAX_RAG_CHUNK_CHARS].strip()
    ]


def _file_suffix(filename: str) -> str:
    dot_index = filename.rfind(".")
    return filename[dot_index:].lower() if dot_index >= 0 else ""


def _original_pdf_path(document_id: str) -> Path | None:
    if Path(document_id).name != document_id:
        return None
    return ORIGINAL_FILE_DIR / f"{document_id}.pdf"


def _file_kind(filename: str, content_type: str) -> str:
    suffix = _file_suffix(filename)
    if suffix == ".pdf":
        return "pdf"
    if suffix == ".docx":
        return "word"
    if suffix in SUPPORTED_TEXT_SUFFIXES:
        return "text"
    if suffix in SUPPORTED_IMAGE_SUFFIXES or content_type.startswith("image/"):
        return "image"
    return "file"


def _resolve_source_type(filename: str, content_type: str, requested_source_type: str) -> str:
    if requested_source_type and requested_source_type not in {"course_material", "file"}:
        return requested_source_type
    return _file_kind(filename, content_type)


def _decode_text(content: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="ignore")


def _extract_docx_text(content: bytes) -> str:
    try:
        from docx import Document

        document = Document(BytesIO(content))
        parts = [paragraph.text for paragraph in document.paragraphs if paragraph.text]
        for table in document.tables:
            for row in table.rows:
                values = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if values:
                    parts.append(" | ".join(values))
        text = "\n\n".join(parts)
        if text.strip():
            return text
    except ImportError:
        pass
    except Exception:
        pass

    return _extract_docx_text_from_xml(content)


def _extract_docx_text_from_xml(content: bytes) -> str:
    try:
        with zipfile.ZipFile(BytesIO(content)) as archive:
            xml_names = [
                name
                for name in archive.namelist()
                if name == "word/document.xml"
                or name.startswith("word/header")
                or name.startswith("word/footer")
            ]
            parts: list[str] = []
            word_namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
            for name in xml_names:
                root = ET.fromstring(archive.read(name))
                for paragraph in root.iter(f"{word_namespace}p"):
                    text = "".join(
                        node.text or ""
                        for node in paragraph.iter(f"{word_namespace}t")
                    ).strip()
                    if text:
                        parts.append(text)
    except (KeyError, ET.ParseError, zipfile.BadZipFile) as exc:
        raise ValueError("无法解析 DOCX 文件，请确认文件未损坏。") from exc

    return "\n\n".join(parts)


def _extract_pdf_text(content: bytes) -> str:
    for module_name in ("pypdf", "PyPDF2"):
        try:
            module = __import__(module_name, fromlist=["PdfReader"])
            reader = module.PdfReader(BytesIO(content))
            pages = [page.extract_text() or "" for page in reader.pages]
            text = "\n\n".join(page.strip() for page in pages if page.strip())
            if text:
                return text
        except ImportError:
            continue
        except Exception:
            continue

    return _extract_pdf_text_fallback(content)


def _extract_pdf_text_fallback(content: bytes) -> str:
    raw = content.decode("latin-1", errors="ignore")
    segments: list[str] = []

    for match in re.finditer(r"\((.*?)\)\s*Tj", raw, flags=re.DOTALL):
        segments.append(_unescape_pdf_string(match.group(1)))

    for array_match in re.finditer(r"\[(.*?)\]\s*TJ", raw, flags=re.DOTALL):
        for text_match in re.finditer(r"\((.*?)\)", array_match.group(1), flags=re.DOTALL):
            segments.append(_unescape_pdf_string(text_match.group(1)))

    text = " ".join(segment.strip() for segment in segments if segment.strip())
    if text:
        return text

    printable = re.sub(r"[^ -~\u4e00-\u9fff]+", " ", raw)
    words = re.findall(
        r"[A-Za-z0-9\u4e00-\u9fff][A-Za-z0-9\u4e00-\u9fff ,.;:!?()/-]{2,}",
        printable,
    )
    return "\n".join(words[:200])


def _extract_image_text(filename: str, content: bytes) -> str:
    try:
        from PIL import Image
    except ImportError:
        return _image_source_fallback(filename)

    try:
        image = Image.open(BytesIO(content))
        image.load()
    except Exception as exc:
        raise ValueError("无法读取图片文件，请确认图片未损坏。") from exc

    try:
        import pytesseract
    except ImportError:
        return _image_source_fallback(filename, image.size)

    try:
        text = pytesseract.image_to_string(image, lang="chi_sim+eng")
    except Exception:
        try:
            text = pytesseract.image_to_string(image)
        except Exception:
            text = ""

    return text.strip() or _image_source_fallback(filename, image.size)


def _image_source_fallback(
    filename: str,
    size: tuple[int, int] | None = None,
) -> str:
    size_text = f"图片尺寸：{size[0]}x{size[1]}。\n" if size else ""
    return (
        f"图片来源：{filename}。\n"
        f"{size_text}"
        "当前环境未识别出图片中的文字，已将图片作为当前 notebook 的来源保存。"
        "如需基于图片具体内容问答，请在复制文字入口粘贴图片中的文字。"
    )


def _unescape_pdf_string(value: str) -> str:
    return (
        value.replace(r"\(", "(")
        .replace(r"\)", ")")
        .replace(r"\\", "\\")
        .replace(r"\n", "\n")
        .replace(r"\r", "\n")
        .replace(r"\t", "\t")
    )
