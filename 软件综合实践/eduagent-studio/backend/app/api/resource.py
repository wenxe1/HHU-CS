from typing import Annotated

from fastapi import APIRouter, Depends, Query
from starlette.responses import JSONResponse

from app.api.dependencies import get_resource_generate_service
from app.models.resource import ResourceType
from app.schemas.common import ApiResponse, error, success
from app.schemas.resource import GenerateResourceRequest
from app.services.resource_service import ResourceGenerateService


router = APIRouter(prefix="/resource", tags=["resource"])


@router.post("/generate", response_model=ApiResponse)
async def generate_resource(
    request: GenerateResourceRequest,
    service: Annotated[
        ResourceGenerateService,
        Depends(get_resource_generate_service),
    ],
):
    result = await service.generate(request)
    return success(result)


@router.get("/list", response_model=ApiResponse)
async def list_resources(
    service: Annotated[
        ResourceGenerateService,
        Depends(get_resource_generate_service),
    ],
    user_id: str | None = None,
    course_id: str | None = None,
    knowledge_point_id: str | None = None,
    resource_type: Annotated[ResourceType | None, Query(alias="type")] = None,
):
    result = await service.list_resources(
        user_id=user_id,
        course_id=course_id,
        knowledge_point_id=knowledge_point_id,
        resource_type=resource_type,
    )
    return success(result)


@router.get("/recommendations", response_model=ApiResponse)
async def get_resource_recommendations(
    service: Annotated[
        ResourceGenerateService,
        Depends(get_resource_generate_service),
    ],
    course_id: str,
    course_name: str | None = None,
    knowledge_point_id: str | None = None,
    query: str | None = None,
):
    result = await service.recommendations(
        course_id=course_id,
        course_name=course_name,
        knowledge_point_id=knowledge_point_id,
        query=query,
    )
    return success(result)


@router.get("/{resource_id}", response_model=ApiResponse)
async def get_resource(
    resource_id: str,
    service: Annotated[
        ResourceGenerateService,
        Depends(get_resource_generate_service),
    ],
):
    resource = await service.get_resource(resource_id)
    if resource is None:
        return JSONResponse(
            status_code=404,
            content=error(404, "resource not found"),
        )
    return success(resource)


@router.delete("/{resource_id}", response_model=ApiResponse)
async def delete_resource(
    resource_id: str,
    service: Annotated[
        ResourceGenerateService,
        Depends(get_resource_generate_service),
    ],
):
    deleted = await service.delete_resource(resource_id)
    if not deleted:
        return JSONResponse(
            status_code=404,
            content=error(404, "resource not found"),
        )
    return success({"resource_id": resource_id, "deleted": True})
