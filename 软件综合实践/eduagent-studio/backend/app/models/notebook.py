from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class Notebook(BaseModel):
    notebook_id: str
    user_id: str
    title: str = Field(min_length=1, max_length=100)
    course_id: str
    knowledge_point_id: str
    recommended_resources: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
