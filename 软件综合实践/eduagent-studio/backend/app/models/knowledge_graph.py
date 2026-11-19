from datetime import UTC, datetime
from typing import Any

from beanie import Document, Indexed
from pydantic import Field


class KnowledgeGraphState(Document):
    graph_id: Indexed(str, unique=True)
    course_name: str = ""
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)
    initial_nodes: list[dict[str, Any]] = Field(default_factory=list)
    initial_edges: list[dict[str, Any]] = Field(default_factory=list)
    source: str = "database"
    updated_reason: str = ""
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "knowledge_graph_state"
