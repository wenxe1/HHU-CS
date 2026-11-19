from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from starlette.responses import FileResponse

from app.api.dependencies import get_code_review_service, get_deepseek_tutor_service
from app.schemas.common import ApiResponse, success
from app.schemas.tutor import CodeReviewRequest, TutorAskRequest
from app.services.code_review_service import CodeReviewService
from app.services.tutor_service import TutorService
from app.services.tutor_preview_service import (
    PreviewError,
    UnsupportedPreviewFileError,
    create_preview,
    preview_file_path,
)


router = APIRouter(prefix="/tutor", tags=["tutor"])


@router.post("/ask", response_model=ApiResponse)
async def ask_tutor(
    request: TutorAskRequest,
    service: Annotated[TutorService, Depends(get_deepseek_tutor_service)],
):
    result = await service.ask(request)
    return success(result)


@router.post("/preview", response_model=ApiResponse)
async def preview_material(file: Annotated[UploadFile, File(...)]):
    try:
        result = await create_preview(file)
    except UnsupportedPreviewFileError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PreviewError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return success(result)


@router.get("/preview/{file_id}")
async def read_preview(file_id: str):
    path = preview_file_path(file_id)
    if path is None:
        raise HTTPException(status_code=404, detail="预览文件不存在或已过期。")

    return FileResponse(
        path,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{path.name}"'},
    )


@router.post("/code-review", response_model=ApiResponse)
async def review_code(
    request: CodeReviewRequest,
    service: Annotated[CodeReviewService, Depends(get_code_review_service)],
):
    result = await service.review(request)
    return success(result)
