from typing import Annotated, Any

from pydantic import BaseModel, Field

from app.models.resource import AuditStatus, ResourceType


class GenerateResourceRequest(BaseModel):
    user_id: str = Field(min_length=1)
    course_id: str = Field(min_length=1)
    knowledge_point_id: str = Field(min_length=1)
    resource_types: Annotated[list[ResourceType], Field(min_length=1)]


class GenerateResourceResult(BaseModel):
    task_id: str
    status: str
    resource_ids: list[str]


class ResourceSummary(BaseModel):
    resource_id: str
    task_id: str
    user_id: str
    course_id: str
    knowledge_point_id: str
    type: ResourceType
    title: str
    audit_status: AuditStatus
    created_at: str


class ResourceDetail(ResourceSummary):
    content: dict[str, Any]
    updated_at: str


class ResourceListResult(BaseModel):
    items: list[ResourceSummary]
    total: int


class ResourceRecommendationItem(BaseModel):
    id: str
    title: str
    authors: list[str]
    source: str
    cover_url: str = ""
    description: str
    level: str
    tags: list[str]
    related_knowledge_points: list[str]
    reason: str
    url: str


class ResourceRecommendationResult(BaseModel):
    items: list[ResourceRecommendationItem]
    source: str
    course_name: str | None = None
    query: str | None = None
    knowledge_point_id: str | None = None
    debug: dict[str, Any] = Field(default_factory=dict)
