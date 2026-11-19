from pydantic import BaseModel, Field


class RAGUploadRequest(BaseModel):
    user_id: str = Field(min_length=1)
    course_id: str = Field(min_length=1)
    notebook_id: str | None = None
    filename: str = Field(min_length=1)
    content: str = Field(min_length=1)
    content_type: str = "text/plain"
    source_type: str = "course_material"
    metadata: dict[str, str] = Field(default_factory=dict)


class RAGDocumentRenameRequest(BaseModel):
    source_title: str = Field(min_length=1, max_length=200)


class RAGDocumentSummary(BaseModel):
    document_id: str
    source_id: str
    user_id: str
    course_id: str
    notebook_id: str
    filename: str
    source_title: str
    source_content: str = ""
    content_type: str
    source_type: str
    upload_status: str
    processing_error: str | None = None
    chunk_count: int
    metadata: dict[str, str]
    created_at: str
    updated_at: str


class RAGUploadResult(BaseModel):
    document_id: str
    source_id: str
    upload_status: str
    chunk_count: int
    chunks: list[dict[str, str | int]]
    document: RAGDocumentSummary | None = None


class RAGDocumentListResult(BaseModel):
    items: list[RAGDocumentSummary]
    total: int
