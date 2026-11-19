import asyncio
from datetime import UTC, datetime
from typing import Any, Protocol
from urllib.parse import quote
from uuid import uuid4

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

from app.models.notebook import Notebook
from app.schemas.notebook import NotebookCreateRequest, NotebookUpdateRequest
from app.services.ai_client import AIClient
from app.services.course_service import (
    KNOWLEDGE_GRAPH_SCHEMA,
    _fallback_graph_for_course,
    _graph_for_storage,
    _normalize_agent_graph,
)


MAX_RECOMMENDED_RESOURCES = 7

NOTEBOOK_RESOURCE_SCHEMA = {
    "items": [
        {
            "id": "string",
            "title": "string",
            "authors": ["string"],
            "source": "string",
            "cover_url": "string",
            "description": "string",
            "level": "string",
            "tags": ["string"],
            "related_knowledge_points": ["string"],
            "reason": "string",
            "url": "https://example.com",
        }
    ]
}


class NotebookRepository(Protocol):
    async def save_notebook(self, notebook: Notebook) -> None:
        ...

    async def list_notebooks(self, user_id: str) -> list[Notebook]:
        ...

    async def get_notebook(self, notebook_id: str, user_id: str) -> Notebook | None:
        ...

    async def update_notebook_title(
        self,
        notebook_id: str,
        user_id: str,
        title: str,
    ) -> Notebook | None:
        ...

    async def delete_notebook(self, notebook_id: str, user_id: str) -> bool:
        ...

    async def count_sources(
        self,
        user_id: str,
        notebook_ids: list[str],
    ) -> dict[str, int]:
        ...

    async def save_initial_knowledge_graph(
        self,
        graph_id: str,
        course_name: str,
        graph: dict[str, Any],
    ) -> None:
        ...


class MongoNotebookRepository:
    def __init__(self, database: AsyncIOMotorDatabase):
        self._notebooks = database["notebooks"]
        self._rag_documents = database["rag_document"]
        self._knowledge_graph_states = database["knowledge_graph_state"]

    async def save_notebook(self, notebook: Notebook) -> None:
        await self._notebooks.create_index([("user_id", 1), ("created_at", -1)])
        await self._notebooks.create_index("notebook_id", unique=True)
        await self._notebooks.insert_one(notebook.model_dump(mode="python"))

    async def list_notebooks(self, user_id: str) -> list[Notebook]:
        cursor = self._notebooks.find(
            {"user_id": user_id},
            {"_id": False},
        ).sort("created_at", -1)
        return [Notebook.model_validate(item) async for item in cursor]

    async def get_notebook(self, notebook_id: str, user_id: str) -> Notebook | None:
        document = await self._notebooks.find_one(
            {"notebook_id": notebook_id, "user_id": user_id},
            {"_id": False},
        )
        return Notebook.model_validate(document) if document else None

    async def update_notebook_title(
        self,
        notebook_id: str,
        user_id: str,
        title: str,
    ) -> Notebook | None:
        now = datetime.now(UTC)
        document = await self._notebooks.find_one_and_update(
            {"notebook_id": notebook_id, "user_id": user_id},
            {"$set": {"title": title, "updated_at": now}},
            projection={"_id": False},
            return_document=ReturnDocument.AFTER,
        )
        return Notebook.model_validate(document) if document else None

    async def save_initial_knowledge_graph(
        self,
        graph_id: str,
        course_name: str,
        graph: dict[str, Any],
    ) -> None:
        stored_payload = _graph_for_storage(graph_id, course_name, graph)
        now = datetime.now(UTC)
        await self._knowledge_graph_states.create_index("graph_id", unique=True)
        await self._knowledge_graph_states.update_one(
            {"graph_id": graph_id},
            {
                "$setOnInsert": {
                    "graph_id": graph_id,
                    "course_name": stored_payload["course_name"],
                    "nodes": stored_payload["nodes"],
                    "edges": stored_payload["edges"],
                    "initial_nodes": stored_payload["nodes"],
                    "initial_edges": stored_payload["edges"],
                    "source": stored_payload["source"],
                    "updated_reason": stored_payload["updated_reason"],
                    "updated_at": now,
                }
            },
            upsert=True,
        )

    async def delete_notebook(self, notebook_id: str, user_id: str) -> bool:
        notebook = await self.get_notebook(notebook_id, user_id)
        if notebook is None:
            return False

        notebook_scope = {
            "user_id": user_id,
            "$or": [
                {"notebook_id": notebook_id},
                {"notebook_id": {"$exists": False}, "course_id": notebook_id},
            ],
        }
        document_ids = [
            item["document_id"]
            async for item in self._rag_documents.find(
                notebook_scope,
                {"_id": False, "document_id": True},
            )
        ]
        if document_ids:
            await self._rag_documents.database["rag_chunk"].delete_many(
                {"document_id": {"$in": document_ids}}
            )
        await self._rag_documents.delete_many(notebook_scope)

        database = self._notebooks.database
        await database["classroom_quiz"].delete_many(notebook_scope)
        flashcard_ids = [
            item["flashcard_set_id"]
            async for item in database["classroom_flashcard_set"].find(
                notebook_scope,
                {"_id": False, "flashcard_set_id": True},
            )
        ]
        if flashcard_ids:
            await database["flashcard_practice_record"].delete_many(
                {"user_id": user_id, "flashcard_set_id": {"$in": flashcard_ids}}
            )
        await database["classroom_flashcard_set"].delete_many(notebook_scope)

        session_ids = [
            item["session_id"]
            async for item in database["classroom_session"].find(
                {"user_id": user_id, "course_id": notebook_id},
                {"_id": False, "session_id": True},
            )
        ]
        if session_ids:
            await database["classroom_scene"].delete_many(
                {"session_id": {"$in": session_ids}}
            )
        await database["classroom_session"].delete_many(
            {"user_id": user_id, "course_id": notebook_id}
        )

        tutor_session_ids = [
            item["session_id"]
            async for item in database["tutor_session"].find(
                {"user_id": user_id, "course_id": notebook_id},
                {"_id": False, "session_id": True},
            )
        ]
        if tutor_session_ids:
            await database["tutor_message"].delete_many(
                {"session_id": {"$in": tutor_session_ids}}
            )
        await database["tutor_session"].delete_many(
            {"user_id": user_id, "course_id": notebook_id}
        )

        await database["agent_task"].delete_many(
            {"user_id": user_id, "course_id": notebook_id}
        )
        await database["learning_resource"].delete_many(
            {"user_id": user_id, "course_id": notebook_id}
        )
        await database["code_review_record"].delete_many(
            {"user_id": user_id, "course_id": notebook_id}
        )
        await database["knowledge_graph_state"].delete_many({"graph_id": notebook_id})
        result = await self._notebooks.delete_one(
            {"notebook_id": notebook_id, "user_id": user_id}
        )
        return result.deleted_count == 1

    async def count_sources(
        self,
        user_id: str,
        notebook_ids: list[str],
    ) -> dict[str, int]:
        if not notebook_ids:
            return {}

        pipeline = [
            {
                "$match": {
                    "user_id": user_id,
                    "upload_status": {"$ne": "failed"},
                    "$or": [
                        {"notebook_id": {"$in": notebook_ids}},
                        {
                            "notebook_id": {"$exists": False},
                            "course_id": {"$in": notebook_ids},
                        },
                    ],
                }
            },
            {
                "$group": {
                    "_id": {"$ifNull": ["$notebook_id", "$course_id"]},
                    "count": {"$sum": 1},
                }
            },
        ]
        return {
            item["_id"]: item["count"]
            async for item in self._rag_documents.aggregate(pipeline)
        }


class InMemoryNotebookRepository:
    def __init__(self):
        self._notebooks: dict[str, Notebook] = {}
        self._source_counts: dict[str, int] = {}
        self._knowledge_graphs: dict[str, dict[str, Any]] = {}

    async def save_notebook(self, notebook: Notebook) -> None:
        self._notebooks[notebook.notebook_id] = notebook.model_copy(deep=True)

    async def list_notebooks(self, user_id: str) -> list[Notebook]:
        notebooks = [
            notebook.model_copy(deep=True)
            for notebook in self._notebooks.values()
            if notebook.user_id == user_id
        ]
        notebooks.sort(key=lambda item: item.created_at, reverse=True)
        return notebooks

    async def get_notebook(self, notebook_id: str, user_id: str) -> Notebook | None:
        notebook = self._notebooks.get(notebook_id)
        if notebook is None or notebook.user_id != user_id:
            return None
        return notebook.model_copy(deep=True)

    async def update_notebook_title(
        self,
        notebook_id: str,
        user_id: str,
        title: str,
    ) -> Notebook | None:
        notebook = self._notebooks.get(notebook_id)
        if notebook is None or notebook.user_id != user_id:
            return None
        updated = notebook.model_copy(
            update={"title": title, "updated_at": datetime.now(UTC)},
            deep=True,
        )
        self._notebooks[notebook_id] = updated
        return updated.model_copy(deep=True)

    async def delete_notebook(self, notebook_id: str, user_id: str) -> bool:
        notebook = self._notebooks.get(notebook_id)
        if notebook is None or notebook.user_id != user_id:
            return False
        del self._notebooks[notebook_id]
        self._source_counts.pop(notebook_id, None)
        return True

    async def count_sources(
        self,
        user_id: str,
        notebook_ids: list[str],
    ) -> dict[str, int]:
        return {
            notebook_id: self._source_counts.get(notebook_id, 0)
            for notebook_id in notebook_ids
        }

    async def save_initial_knowledge_graph(
        self,
        graph_id: str,
        course_name: str,
        graph: dict[str, Any],
    ) -> None:
        stored_payload = _graph_for_storage(graph_id, course_name, graph)
        self._knowledge_graphs.setdefault(
            graph_id,
            {
                **stored_payload,
                "initial_nodes": stored_payload["nodes"],
                "initial_edges": stored_payload["edges"],
            },
        )


class NotebookService:
    def __init__(
        self,
        repository: NotebookRepository,
        ai_client: AIClient | None = None,
    ):
        self._repository = repository
        self._ai_client = ai_client

    async def create(self, request: NotebookCreateRequest) -> dict[str, object]:
        title = request.title.strip()
        if not title:
            raise ValueError("notebook title is required")

        notebook_id = str(uuid4())
        recommended_resources, initial_graph = await asyncio.gather(
            _generate_notebook_resources(
                self._ai_client,
                title,
            ),
            _generate_initial_knowledge_graph(
                self._ai_client,
                notebook_id,
                title,
            ),
        )
        notebook = Notebook(
            notebook_id=notebook_id,
            user_id=request.user_id,
            title=title,
            course_id=notebook_id,
            knowledge_point_id=notebook_id,
            recommended_resources=recommended_resources,
        )
        await self._repository.save_notebook(notebook)
        await self._repository.save_initial_knowledge_graph(
            notebook_id,
            title,
            initial_graph,
        )
        return _to_response(notebook, source_count=0)

    async def update(
        self,
        notebook_id: str,
        user_id: str,
        request: NotebookUpdateRequest,
    ) -> dict[str, object] | None:
        title = request.title.strip()
        if not title:
            raise ValueError("notebook title is required")

        notebook = await self._repository.update_notebook_title(
            notebook_id=notebook_id,
            user_id=user_id,
            title=title,
        )
        if notebook is None:
            return None
        source_counts = await self._repository.count_sources(user_id, [notebook_id])
        return _to_response(notebook, source_counts.get(notebook_id, 0))

    async def delete(self, notebook_id: str, user_id: str) -> bool:
        return await self._repository.delete_notebook(notebook_id, user_id)

    async def list(self, user_id: str) -> list[dict[str, object]]:
        notebooks = await self._repository.list_notebooks(user_id)
        source_counts = await self._repository.count_sources(
            user_id,
            [notebook.notebook_id for notebook in notebooks],
        )
        return [
            _to_response(
                notebook,
                source_count=source_counts.get(notebook.notebook_id, 0),
            )
            for notebook in notebooks
        ]

    async def get(self, notebook_id: str, user_id: str) -> dict[str, object] | None:
        notebook = await self._repository.get_notebook(notebook_id, user_id)
        if notebook is None:
            return None
        source_counts = await self._repository.count_sources(user_id, [notebook_id])
        return _to_response(notebook, source_counts.get(notebook_id, 0))


def _to_response(notebook: Notebook, source_count: int) -> dict[str, object]:
    result = notebook.model_dump(mode="json")
    result["source_count"] = source_count
    return result


async def _generate_notebook_resources(
    ai_client: AIClient | None,
    notebook_title: str,
) -> list[dict[str, Any]]:
    fallback = _fallback_notebook_resources(notebook_title)
    if ai_client is None:
        return fallback
    system_prompt = (
        "You are EduAgent Studio's learning resource curator. "
        "Generate stable public learning resource links from the notebook title. "
        "Return at most 7 items, preferably exactly 7 when relevant public resources exist. "
        "Every item must include a real-looking http or https URL and concise Chinese metadata."
    )
    user_prompt = (
        f"notebook_title: {notebook_title}\n"
        "Create public learning-resource recommendations for this notebook. "
        "Do not return more than 7 items. Prefer official courses, textbooks, docs, labs, "
        "or high-quality open educational resources."
    )
    try:
        generated = await ai_client.generate_json(
            agent_name="Notebook Resource Agent",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_schema=NOTEBOOK_RESOURCE_SCHEMA,
            use_reasoning=False,
        )
        resources = _normalize_notebook_resources(generated, notebook_title)
        return resources or fallback
    except Exception:
        return fallback


async def _generate_initial_knowledge_graph(
    ai_client: AIClient | None,
    notebook_id: str,
    notebook_title: str,
) -> dict[str, Any]:
    fallback = _fallback_graph_for_course(
        notebook_id,
        notebook_title,
        "Initial fallback graph generated for notebook creation.",
    )
    if ai_client is None:
        return fallback
    system_prompt = (
        "You are EduAgent Studio's knowledge graph agent. "
        "Generate the initial knowledge graph from the notebook title. "
        "Use 6 to 10 nodes when possible. Node importance must be one of "
        "core, important, normal; mastery must be unknown. "
        "Node labels must use Chinese characters only; do not use English letters, acronyms, digits, or symbols."
    )
    user_prompt = (
        f"notebook_id: {notebook_id}\n"
        f"notebook_title: {notebook_title}\n"
        "Generate the initial graph. Edges should express prerequisite, related, or advanced relations."
    )
    try:
        generated = await ai_client.generate_json(
            agent_name="Notebook Knowledge Graph Agent",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_schema=KNOWLEDGE_GRAPH_SCHEMA,
            use_reasoning=False,
        )
        return _normalize_agent_graph(generated, notebook_id, notebook_title)
    except Exception:
        return fallback


def _normalize_notebook_resources(
    payload: dict[str, Any],
    notebook_title: str,
) -> list[dict[str, Any]]:
    raw_items = payload.get("items") if isinstance(payload, dict) else []
    resources: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    for index, raw_item in enumerate(raw_items if isinstance(raw_items, list) else []):
        if not isinstance(raw_item, dict):
            continue
        title = _clean_resource_text(raw_item.get("title"))
        url = _clean_resource_text(raw_item.get("url"))
        if not title or not url.startswith(("http://", "https://")):
            continue
        title_key = title.lower()
        url_key = url.rstrip("/")
        if title_key in seen_titles or url_key in seen_urls:
            continue
        seen_titles.add(title_key)
        seen_urls.add(url_key)
        resources.append(
            {
                "id": _clean_resource_text(raw_item.get("id")) or f"notebook-resource-{index + 1}",
                "title": title,
                "authors": _clean_resource_text_list(raw_item.get("authors")),
                "source": _clean_resource_text(raw_item.get("source")) or "AI 推荐",
                "cover_url": _clean_resource_text(raw_item.get("cover_url")),
                "description": _clean_resource_text(raw_item.get("description")) or title,
                "level": _clean_resource_text(raw_item.get("level")) or "推荐",
                "tags": _clean_resource_text_list(raw_item.get("tags")) or [notebook_title],
                "related_knowledge_points": _clean_resource_text_list(
                    raw_item.get("related_knowledge_points")
                )
                or [notebook_title],
                "reason": _clean_resource_text(raw_item.get("reason")) or f"适合学习 {notebook_title}",
                "url": url,
            }
        )
        if len(resources) >= MAX_RECOMMENDED_RESOURCES:
            break
    return resources


def _fallback_notebook_resources(notebook_title: str) -> list[dict[str, Any]]:
    topic = notebook_title or "当前笔记本"
    query = quote(topic)
    templates = [
        ("mit-ocw", f"MIT OpenCourseWare: {topic}", "MIT OpenCourseWare", f"https://ocw.mit.edu/search/?q={query}", "公开课程与讲义检索。", "进阶"),
        ("coursera", f"Coursera: {topic}", "Coursera", f"https://www.coursera.org/search?query={query}", "结构化课程与专项训练检索。", "课程"),
        ("edx", f"edX: {topic}", "edX", f"https://www.edx.org/search?q={query}", "高校与机构开放课程检索。", "课程"),
        ("khan", f"Khan Academy: {topic}", "Khan Academy", f"https://www.khanacademy.org/search?page_search_query={query}", "基础概念讲解和练习检索。", "入门"),
        ("wikipedia", f"Wikipedia: {topic}", "Wikipedia", f"https://en.wikipedia.org/w/index.php?search={query}", "百科式背景知识入口。", "参考"),
        ("github", f"GitHub Topics: {topic}", "GitHub", f"https://github.com/search?q={query}&type=repositories", "相关开源项目与示例代码检索。", "实践"),
        ("bilibili", f"哔哩哔哩: {topic}", "bilibili", f"https://search.bilibili.com/all?keyword={query}", "中文视频课程与讲解检索。", "视频"),
    ]
    return [
        {
            "id": f"fallback-{resource_id}",
            "title": title,
            "authors": [],
            "source": source,
            "cover_url": "",
            "description": description,
            "level": level,
            "tags": [topic],
            "related_knowledge_points": [topic],
            "reason": f"围绕 {topic} 提供可继续筛选的学习入口。",
            "url": url,
        }
        for resource_id, title, source, url, description, level in templates[:MAX_RECOMMENDED_RESOURCES]
    ]


def _clean_resource_text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _clean_resource_text_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    result = []
    seen = set()
    for item in value:
        text = _clean_resource_text(item)
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result
