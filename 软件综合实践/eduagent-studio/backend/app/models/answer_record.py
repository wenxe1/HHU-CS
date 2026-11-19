from datetime import datetime
from typing import Optional

from beanie import Document, PydanticObjectId
from pydantic import Field


class AnswerRecord(Document):
    user_id: PydanticObjectId
    question_id: PydanticObjectId
    user_answer: str
    is_correct: bool = False
    time_spent: Optional[int] = None
    mistake_type: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "answer_records"
        indexes = [
            [("user_id", 1)],
            [("user_id", 1), ("question_id", 1)],
        ]
