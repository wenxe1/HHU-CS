from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


ResourceType = Literal["lecture", "exercise", "mindmap", "slide", "code_lab"]
AuditStatus = Literal["pending", "approved", "rejected"]


class LearningResource(BaseModel):
    resource_id: str
    task_id: str
    user_id: str
    course_id: str
    knowledge_point_id: str
    type: ResourceType
    title: str
    content: dict[str, Any] = Field(default_factory=dict)
    audit_status: AuditStatus = "pending"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
