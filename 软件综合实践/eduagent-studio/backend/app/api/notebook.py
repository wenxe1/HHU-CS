from typing import Annotated

from fastapi import APIRouter, Depends
from starlette.responses import JSONResponse

from app.api.dependencies import get_notebook_service
from app.schemas.common import ApiResponse, error, success
from app.schemas.notebook import NotebookCreateRequest, NotebookUpdateRequest
from app.services.notebook_service import NotebookService


router = APIRouter(prefix="/notebooks", tags=["notebooks"])


@router.post("", response_model=ApiResponse)
async def create_notebook(
    request: NotebookCreateRequest,
    service: Annotated[NotebookService, Depends(get_notebook_service)],
):
    try:
        result = await service.create(request)
    except ValueError as exc:
        return JSONResponse(status_code=400, content=error(400, str(exc)))
    return success(result)


@router.get("", response_model=ApiResponse)
async def list_notebooks(
    user_id: str,
    service: Annotated[NotebookService, Depends(get_notebook_service)],
):
    return success(await service.list(user_id))


@router.get("/{notebook_id}", response_model=ApiResponse)
async def get_notebook(
    notebook_id: str,
    user_id: str,
    service: Annotated[NotebookService, Depends(get_notebook_service)],
):
    notebook = await service.get(notebook_id, user_id)
    if notebook is None:
        return JSONResponse(
            status_code=404,
            content=error(404, "notebook not found"),
        )
    return success(notebook)


@router.patch("/{notebook_id}", response_model=ApiResponse)
async def update_notebook(
    notebook_id: str,
    user_id: str,
    request: NotebookUpdateRequest,
    service: Annotated[NotebookService, Depends(get_notebook_service)],
):
    try:
        notebook = await service.update(notebook_id, user_id, request)
    except ValueError as exc:
        return JSONResponse(status_code=400, content=error(400, str(exc)))
    if notebook is None:
        return JSONResponse(
            status_code=404,
            content=error(404, "notebook not found"),
        )
    return success(notebook)


@router.delete("/{notebook_id}", response_model=ApiResponse)
async def delete_notebook(
    notebook_id: str,
    user_id: str,
    service: Annotated[NotebookService, Depends(get_notebook_service)],
):
    deleted = await service.delete(notebook_id, user_id)
    if not deleted:
        return JSONResponse(
            status_code=404,
            content=error(404, "notebook not found"),
        )
    return success({"notebook_id": notebook_id, "deleted": True})
