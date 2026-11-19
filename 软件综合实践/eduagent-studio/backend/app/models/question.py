from datetime import datetime
from enum import Enum
from typing import Optional

from beanie import Document, PydanticObjectId
from pydantic import Field


class QuestionType(str, Enum):
    CHOICE = "choice"
    FILL = "fill"
    CODE = "code"


class Question(Document):
    knowledge_point_id: PydanticObjectId
    question_type: QuestionType
    content: str
    options: Optional[list[str]] = None
    answer: str
    explanation: Optional[str] = None
    difficulty: str = "basic"
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "questions"
        indexes = [
            [("knowledge_point_id", 1)],
        ]
