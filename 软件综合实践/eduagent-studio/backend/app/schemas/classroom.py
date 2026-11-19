from typing import Any

from pydantic import BaseModel, Field


class ClassroomGenerateRequest(BaseModel):
    user_id: str = Field(min_length=1)
    course_id: str = Field(min_length=1)
    notebook_id: str | None = None
    knowledge_point_id: str = Field(min_length=1)
    topic: str | None = None
    source_document_ids: list[str] = Field(default_factory=list)


class ClassroomQuizGenerateRequest(BaseModel):
    user_id: str = Field(min_length=1)
    course_id: str = Field(min_length=1)
    notebook_id: str | None = None
    knowledge_point_id: str | None = None
    source_document_ids: list[str] = Field(default_factory=list)
    question_count: int | None = Field(default=None, ge=1, le=10)
    difficulty: str = "medium"


class ClassroomFlashcardsGenerateRequest(BaseModel):
    user_id: str = Field(min_length=1)
    course_id: str = Field(min_length=1)
    notebook_id: str | None = None
    knowledge_point_id: str | None = None
    source_document_ids: list[str] = Field(default_factory=list)
    card_count: int | None = Field(default=None, ge=1, le=10)
    difficulty: str = "medium"


class ClassroomGenerateResult(BaseModel):
    session_id: str
    title: str
    status: str
    scene_count: int
    scene_types: list[str]


class ClassroomSceneResponse(BaseModel):
    scene_id: str
    session_id: str
    scene_type: str
    title: str
    content: dict[str, Any]
    order: int
    speaker: str | None = None
    actions: list[dict[str, Any]]
    created_at: str


class ClassroomDetail(BaseModel):
    session_id: str
    user_id: str
    course_id: str
    knowledge_point_id: str
    title: str
    description: str
    learning_goals: list[str]
    agents: list[dict[str, Any]]
    status: str
    scene_ids: list[str]
    scenes: list[ClassroomSceneResponse]
    created_at: str
    updated_at: str


class QuizQuestionResponse(BaseModel):
    question_id: str
    type: str
    stem: str
    options: list[str]
    answer: str
    explanation: str
    option_explanations: dict[str, str] = Field(default_factory=dict)


class ClassroomQuizGenerateResult(BaseModel):
    quiz_id: str
    notebook_id: str | None = None
    title: str
    questions: list[QuizQuestionResponse]
    source_document_ids: list[str]
    created_at: str | None = None
    updated_at: str | None = None


class FlashcardResponse(BaseModel):
    card_id: str
    front: str
    back: str


class ClassroomFlashcardsGenerateResult(BaseModel):
    flashcard_set_id: str
    notebook_id: str | None = None
    title: str
    cards: list[FlashcardResponse]
    source_document_ids: list[str]
    created_at: str | None = None
    updated_at: str | None = None


class FlashcardPracticeRecordRequest(BaseModel):
    user_id: str = Field(min_length=1)
    course_id: str = Field(min_length=1)
    flashcard_set_id: str = Field(min_length=1)
    attempt_id: str = Field(min_length=1)
    study_card_ids: list[str] = Field(min_length=1)
    card_id: str = Field(min_length=1)
    result: str = Field(pattern="^(correct|incorrect)$")


class FlashcardPracticeResetRequest(BaseModel):
    user_id: str = Field(min_length=1)


class FlashcardPracticeRecordResponse(BaseModel):
    record_id: str
    user_id: str
    course_id: str
    flashcard_set_id: str
    attempt_id: str
    study_card_ids: list[str]
    card_id: str
    result: str
    attempt_completed: bool
    created_at: str
    updated_at: str


class QuizPracticeRecordRequest(BaseModel):
    user_id: str = Field(min_length=1)
    course_id: str = Field(min_length=1)
    quiz_id: str = Field(min_length=1)
    question_id: str = Field(min_length=1)
    selected_answer: str = Field(min_length=1)


class QuizPracticeRecordResponse(BaseModel):
    record_id: str
    user_id: str
    course_id: str
    notebook_id: str | None = None
    quiz_id: str
    question_id: str
    selected_answer: str
    correct_answer: str
    is_correct: bool
    created_at: str
    updated_at: str


class UserProfileGenerateRequest(BaseModel):
    user_id: str = Field(min_length=1)
    course_id: str = Field(min_length=1)
    notebook_id: str | None = None
    force_refresh: bool = False


class ClassroomStudioListResult(BaseModel):
    quizzes: list[ClassroomQuizGenerateResult]
    flashcard_sets: list[ClassroomFlashcardsGenerateResult]
    flashcard_records: list[FlashcardPracticeRecordResponse]


class UserProfileRadarMetric(BaseModel):
    key: str
    label: str
    score: int = Field(ge=0, le=100)
    reason: str


class UserProfileRecommendation(BaseModel):
    title: str
    detail: str
    priority: str = "medium"


class UserProfileLearningResource(BaseModel):
    title: str
    url: str
    language: str = "zh"
    reason: str


class UserProfileSignals(BaseModel):
    conversation_count: int
    message_count: int
    quiz_attempt_count: int
    flashcard_attempt_count: int
    quiz_accuracy: float
    flashcard_accuracy: float


class UserProfileWindow(BaseModel):
    conversation_limit: int
    quiz_practice_limit: int
    flashcard_practice_limit: int


class UserProfileResult(BaseModel):
    user_id: str
    course_id: str
    notebook_id: str | None = None
    is_unlocked: bool
    generated_at: str
    window: UserProfileWindow
    signals: UserProfileSignals
    summary: str
    radar: list[UserProfileRadarMetric]
    learning_traits: list[str]
    strengths: list[str]
    risks: list[str]
    recommendations: list[UserProfileRecommendation]
    learning_resources: list[UserProfileLearningResource] = Field(default_factory=list)
