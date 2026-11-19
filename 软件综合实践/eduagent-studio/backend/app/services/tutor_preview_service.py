from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile


PREVIEW_DIR = Path(__file__).resolve().parents[2] / ".tmp" / "previews"
SUPPORTED_SUFFIX = ".pdf"


class PreviewError(Exception):
    pass


class UnsupportedPreviewFileError(PreviewError):
    pass


def preview_file_path(file_id: str) -> Path | None:
    if Path(file_id).name != file_id:
        return None

    path = PREVIEW_DIR / file_id
    if path.suffix.lower() != ".pdf" or not path.is_file():
        return None

    return path


def create_preview_from_bytes(filename: str, content: bytes) -> dict[str, str]:
    original_filename = Path(filename or "material").name
    suffix = Path(original_filename).suffix.lower()
    if suffix != SUPPORTED_SUFFIX:
        raise UnsupportedPreviewFileError("智能辅导页仅支持 PDF 预览，请选择 PDF 文件。")

    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    file_token = str(uuid4())
    uploaded_path = PREVIEW_DIR / f"{file_token}.pdf"
    uploaded_path.write_bytes(content)

    return {
        "preview_type": "pdf",
        "preview_url": f"/api/tutor/preview/{uploaded_path.name}",
        "filename": original_filename,
        "original_type": "pdf",
    }


async def create_preview(file: UploadFile) -> dict[str, str]:
    try:
        content = await file.read()
        return create_preview_from_bytes(file.filename or "material", content)
    finally:
        await file.close()
