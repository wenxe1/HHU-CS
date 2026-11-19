from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from starlette.responses import FileResponse, JSONResponse

from app.api.dependencies import get_rag_service
from app.schemas.common import ApiResponse, error, success
from app.schemas.rag import RAGDocumentRenameRequest, RAGUploadRequest
from app.services.rag_service import RAGService


router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/upload", response_model=ApiResponse)
async def upload_document(
    request: RAGUploadRequest,
    service: Annotated[RAGService, Depends(get_rag_service)],
):
    result = await service.upload(request)
    return success(result)


@router.post("/upload-file", response_model=ApiResponse)
async def upload_document_file(
    background_tasks: BackgroundTasks,
    user_id: Annotated[str, Form(min_length=1)],
    course_id: Annotated[str, Form(min_length=1)],
    file: Annotated[UploadFile, File()],
    service: Annotated[RAGService, Depends(get_rag_service)],
    source_type: Annotated[str, Form()] = "course_material",
    notebook_id: Annotated[str | None, Form()] = None,
):
    content = await file.read()
    try:
        document = await service.create_file_source(
            user_id=user_id,
            course_id=course_id,
            notebook_id=notebook_id,
            filename=file.filename or "untitled",
            content_type=file.content_type or "application/octet-stream",
            content_size=len(content),
            source_type=source_type,
        )
        document = await service.save_original_pdf_file(document, content)
    except ValueError as exc:
        return JSONResponse(status_code=400, content=error(400, str(exc)))

    background_tasks.add_task(service.process_file_source, document, content)
    return success(service.format_upload_result(document))


@router.get("/documents", response_model=ApiResponse)
async def list_documents(
    service: Annotated[RAGService, Depends(get_rag_service)],
    user_id: str | None = None,
    course_id: str | None = None,
    notebook_id: str | None = None,
):
    result = await service.list_documents(
        user_id=user_id,
        course_id=course_id,
        notebook_id=notebook_id,
    )
    return success(result)


@router.get("/documents/{document_id}/file")
async def read_document_file(
    document_id: str,
    service: Annotated[RAGService, Depends(get_rag_service)],
):
    path = await service.get_original_file_path(document_id)
    if path is None:
        raise HTTPException(status_code=404, detail="source file not found")

    return FileResponse(
        path,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{path.name}"'},
    )


@router.delete("/documents/{document_id}", response_model=ApiResponse)
async def delete_document(
    document_id: str,
    service: Annotated[RAGService, Depends(get_rag_service)],
):
    deleted = await service.delete_document(document_id)
    if not deleted:
        return JSONResponse(
            status_code=404,
            content=error(404, "document not found"),
        )
    return success({"document_id": document_id, "deleted": True})


@router.patch("/documents/{document_id}", response_model=ApiResponse)
async def rename_document(
    document_id: str,
    request: RAGDocumentRenameRequest,
    service: Annotated[RAGService, Depends(get_rag_service)],
):
    try:
        document = await service.rename_document(
            document_id=document_id,
            source_title=request.source_title,
        )
    except ValueError as exc:
        return JSONResponse(status_code=400, content=error(400, str(exc)))
    if document is None:
        return JSONResponse(
            status_code=404,
            content=error(404, "document not found"),
        )
    return success(document)
