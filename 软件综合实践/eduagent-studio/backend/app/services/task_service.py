from app.db.repositories import ResourceTaskRepository


class TaskService:
    def __init__(self, repository: ResourceTaskRepository):
        self._repository = repository

    async def get_task(self, task_id: str) -> dict | None:
        task = await self._repository.get_task(task_id)
        if task is None:
            return None
        return task.model_dump(mode="json")

    async def get_task_events(self, task_id: str) -> dict | None:
        task = await self._repository.get_task(task_id)
        if task is None:
            return None
        return {
            "task_id": task.task_id,
            "events": [event.model_dump(mode="json") for event in task.events],
        }
