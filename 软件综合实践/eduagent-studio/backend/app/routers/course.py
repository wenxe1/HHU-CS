from typing import Any

from fastapi import APIRouter, HTTPException

from app.schemas.common import ApiResponse
from app.schemas.course import (
    CourseCreateRequest,
    KnowledgeGraphSaveRequest,
    KnowledgeGraphUpdateRequest,
    KnowledgePointCreateRequest,
)
from app.services.course_service import CourseService

router = APIRouter(tags=["课程与知识点"])
course_service = CourseService()


@router.get("/courses", response_model=ApiResponse[list[dict]])
async def list_courses():
    courses = await course_service.list_courses()
    return ApiResponse(data=courses)


@router.post("/courses", response_model=ApiResponse[dict])
async def create_course(data: CourseCreateRequest):
    course = await course_service.create_course(data)
    return ApiResponse(data=CourseService._course_to_dict(course))


@router.get("/courses/{course_id}/knowledge-points", response_model=ApiResponse[list[dict]])
async def list_knowledge_points(course_id: str):
    kps = await course_service.list_knowledge_points(course_id)
    return ApiResponse(data=kps)


@router.post("/knowledge-points", response_model=ApiResponse[dict])
async def create_knowledge_point(data: KnowledgePointCreateRequest):
    kp = await course_service.create_knowledge_point(data)
    return ApiResponse(data=CourseService._kp_to_dict(kp))


@router.get("/courses/{course_id}/knowledge-graph", response_model=ApiResponse[Any])
async def get_knowledge_graph(course_id: str):
    graph = await course_service.get_knowledge_point_graph(course_id)
    return ApiResponse(data=graph)


@router.put("/courses/{course_id}/knowledge-graph", response_model=ApiResponse[dict])
async def save_knowledge_graph(course_id: str, data: KnowledgeGraphSaveRequest):
    graph = await course_service.save_knowledge_graph(
        course_id,
        data.graph,
        course_name=data.course_name,
    )
    return ApiResponse(data=graph)


@router.post("/courses/{course_id}/knowledge-graph/generate", response_model=ApiResponse[dict])
async def generate_knowledge_graph(course_id: str):
    try:
        graph = await course_service.generate_knowledge_graph(course_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ApiResponse(data=graph)


@router.post("/courses/{course_id}/knowledge-graph/update", response_model=ApiResponse[dict])
async def update_knowledge_graph(course_id: str, data: KnowledgeGraphUpdateRequest):
    graph = await course_service.update_knowledge_graph(course_id, data)
    return ApiResponse(data=graph)
