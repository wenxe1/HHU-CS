from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class CourseCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    teacher_id: Optional[str] = None


class CourseResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    teacher_id: Optional[str] = None
    created_at: datetime


class KnowledgePointCreateRequest(BaseModel):
    course_id: str
    chapter: Optional[str] = None
    name: str
    description: Optional[str] = None
    difficulty: str = "basic"
    prerequisites: list[str] = []
    order: int = 0


class KnowledgePointResponse(BaseModel):
    id: str
    course_id: str
    chapter: Optional[str] = None
    name: str
    description: Optional[str] = None
    difficulty: str = "basic"
    prerequisites: list[str] = []
    order: int = 0
    created_at: datetime


class KnowledgeGraphUpdateRequest(BaseModel):
    course_name: Optional[str] = None
    selected_node_id: Optional[str] = None
    selected_node_name: Optional[str] = None
    user_question: Optional[str] = None
    current_graph: dict[str, Any] = Field(default_factory=dict)


class KnowledgeGraphSaveRequest(BaseModel):
    course_name: Optional[str] = None
    graph: dict[str, Any] = Field(default_factory=dict)
