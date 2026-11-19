from pydantic import BaseModel


class TaskEventResponse(BaseModel):
    stage: str
    message: str
    progress: int
    created_at: str


class TaskDetail(BaseModel):
    task_id: str
    user_id: str
    course_id: str
    knowledge_point_id: str
    status: str
    progress: int
    current_stage: str
    events: list[TaskEventResponse]
    resource_ids: list[str]
    created_at: str
    updated_at: str


class TaskEventsResult(BaseModel):
    task_id: str
    events: list[TaskEventResponse]
