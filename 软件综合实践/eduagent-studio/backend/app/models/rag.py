from datetime import UTC, datetime
from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator


UploadStatus = Literal["processing", "success", "failed"]


class RAGDocument(BaseModel):
    document_id: str
    source_id: str | None = None
    user_id: str
    course_id: str
    notebook_id: str | None = None
    filename: str
    source_title: str | None = None
    source_content: str = ""
    content_type: str = "text/plain"
    source_type: str = "course_material"
    upload_status: UploadStatus = "success"
    processing_error: str | None = None
    chunk_count: int = 0
    metadata: dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def fill_source_fields(self) -> Self:
        if not self.source_id:
            self.source_id = self.document_id
        if not self.notebook_id:
            self.notebook_id = self.course_id
        if not self.source_title:
            self.source_title = self.filename
        return self


class RAGChunk(BaseModel):
    chunk_id: str
    document_id: str
    course_id: str
    chunk_index: int
    text: str
    embedding: list[float] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
