from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


TaskStatus = Literal["pending", "running", "completed", "failed"]


class TaskEvent(BaseModel):
    stage: str
    message: str
    progress: int = Field(ge=0, le=100)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AgentTask(BaseModel):
    task_id: str
    user_id: str
    course_id: str
    knowledge_point_id: str
    status: TaskStatus = "pending"
    progress: int = Field(default=0, ge=0, le=100)
    current_stage: str = "pending"
    events: list[TaskEvent] = Field(default_factory=list)
    resource_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
