from pydantic import BaseModel, Field


class NotebookCreateRequest(BaseModel):
    user_id: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=100)


class NotebookUpdateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=100)
