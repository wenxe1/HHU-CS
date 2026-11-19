from datetime import datetime
from enum import Enum
from typing import Optional

from beanie import Document, PydanticObjectId
from pydantic import Field


class DifficultyLevel(str, Enum):
    BASIC = "basic"
    MEDIUM = "medium"
    HARD = "hard"
    COMPREHENSIVE = "comprehensive"


class KnowledgePoint(Document):
    course_id: PydanticObjectId
    chapter: Optional[str] = None
    name: str
    description: Optional[str] = None
    difficulty: DifficultyLevel = DifficultyLevel.BASIC
    prerequisites: list[PydanticObjectId] = Field(default_factory=list)
    order: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "knowledge_points"
        indexes = [
            [("course_id", 1)],
        ]
