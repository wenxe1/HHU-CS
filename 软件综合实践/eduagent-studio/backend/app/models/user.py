from datetime import datetime
from enum import Enum
from typing import Optional

from beanie import Document
from pydantic import Field


class UserRole(str, Enum):
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"


class User(Document):
    name: str
    email: str
    role: UserRole = UserRole.STUDENT
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "users"
        indexes = [
            [("email", 1)],
        ]
