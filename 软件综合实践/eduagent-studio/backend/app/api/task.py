from typing import Annotated

from fastapi import APIRouter, Depends
from starlette.responses import JSONResponse

from app.api.dependencies import get_task_service
from app.schemas.common import ApiResponse, error, success
from app.services.task_service import TaskService


router = APIRouter(prefix="/task", tags=["task"])


@router.get("/{task_id}", response_model=ApiResponse)
async def get_task(
    task_id: str,
    service: Annotated[TaskService, Depends(get_task_service)],
):
    task = await service.get_task(task_id)
    if task is None:
        return JSONResponse(status_code=404, content=error(404, "task not found"))
    return success(task)


@router.get("/{task_id}/events", response_model=ApiResponse)
async def get_task_events(
    task_id: str,
    service: Annotated[TaskService, Depends(get_task_service)],
):
    events = await service.get_task_events(task_id)
    if events is None:
        return JSONResponse(status_code=404, content=error(404, "task not found"))
    return success(events)
