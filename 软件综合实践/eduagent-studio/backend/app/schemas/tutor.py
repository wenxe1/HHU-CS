from typing import Any

from pydantic import BaseModel, Field


class TutorAskRequest(BaseModel):
    user_id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    course_id: str | None = None
    course_name: str | None = None
    notebook_id: str | None = None
    visit_id: str | None = None
    knowledge_point_id: str | None = None
    knowledge_point_name: str | None = None
    source_document_ids: list[str] = Field(default_factory=list)
    student_profile: dict[str, Any] = Field(default_factory=dict)
    code_snippet: str | None = None


class TutorAskResult(BaseModel):
    session_id: str
    answer: str
    guidance_steps: list[str]
    follow_up_questions: list[str]
    citations: list[dict[str, Any]] = Field(default_factory=list)
    personalization: dict[str, Any]


class CodeReviewRequest(BaseModel):
    user_id: str = Field(min_length=1)
    language: str = Field(min_length=1)
    code: str = Field(min_length=1)
    course_id: str | None = None
    knowledge_point_id: str | None = None
    error_message: str | None = None


class CodeReviewIssueResponse(BaseModel):
    category: str
    severity: str
    title: str
    detail: str
    suggestion: str
    line: int | None = None


class CodeReviewResult(BaseModel):
    record_id: str
    language: str
    summary: str
    issues: list[CodeReviewIssueResponse]
    suggestions: list[str]
    next_steps: list[str]
