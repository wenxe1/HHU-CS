from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


TutorMessageRole = Literal["user", "assistant"]
IssueSeverity = Literal["info", "warning", "error"]


class TutorSession(BaseModel):
    session_id: str
    user_id: str
    course_id: str | None = None
    notebook_id: str | None = None
    visit_id: str | None = None
    knowledge_point_id: str | None = None
    question: str
    status: str = "completed"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TutorMessage(BaseModel):
    message_id: str
    session_id: str
    role: TutorMessageRole
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CodeReviewIssue(BaseModel):
    category: str
    severity: IssueSeverity
    title: str
    detail: str
    suggestion: str
    line: int | None = None


class CodeReviewRecord(BaseModel):
    record_id: str
    user_id: str
    language: str
    code: str
    course_id: str | None = None
    knowledge_point_id: str | None = None
    error_message: str | None = None
    summary: str
    issues: list[CodeReviewIssue]
    suggestions: list[str]
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
