from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


SceneType = Literal[
    "teacher_explain",
    "classmate_question",
    "discussion",
    "slide",
    "quiz",
    "whiteboard",
    "interactive",
    "code_interactive",
    "pbl",
    "homework",
    "summary",
]


class ClassroomSession(BaseModel):
    session_id: str
    user_id: str
    course_id: str
    knowledge_point_id: str
    title: str
    description: str
    learning_goals: list[str]
    agents: list[dict[str, Any]]
    status: str = "completed"
    scene_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ClassroomScene(BaseModel):
    scene_id: str
    session_id: str
    scene_type: SceneType
    title: str
    content: dict[str, Any]
    order: int
    speaker: str | None = None
    actions: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ClassroomQuizArtifact(BaseModel):
    quiz_id: str
    user_id: str
    course_id: str
    notebook_id: str | None = None
    knowledge_point_id: str | None = None
    title: str
    questions: list[dict[str, Any]]
    source_document_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ClassroomFlashcardSet(BaseModel):
    flashcard_set_id: str
    user_id: str
    course_id: str
    notebook_id: str | None = None
    knowledge_point_id: str | None = None
    title: str
    cards: list[dict[str, Any]]
    source_document_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class FlashcardPracticeRecord(BaseModel):
    record_id: str
    user_id: str
    course_id: str
    flashcard_set_id: str
    attempt_id: str = "legacy"
    study_card_ids: list[str] = Field(default_factory=list)
    card_id: str
    result: Literal["correct", "incorrect"]
    attempt_completed: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class QuizPracticeRecord(BaseModel):
    record_id: str
    user_id: str
    course_id: str
    notebook_id: str | None = None
    quiz_id: str
    question_id: str
    selected_answer: str
    correct_answer: str
    is_correct: bool
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
