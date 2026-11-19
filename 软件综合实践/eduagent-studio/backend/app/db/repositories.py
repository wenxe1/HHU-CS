from math import sqrt
from typing import Any, Protocol

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.audit import ContentAudit
from app.models.classroom import (
    ClassroomFlashcardSet,
    ClassroomQuizArtifact,
    ClassroomScene,
    ClassroomSession,
    FlashcardPracticeRecord,
    QuizPracticeRecord,
)
from app.models.rag import RAGChunk, RAGDocument
from app.models.resource import LearningResource, ResourceType
from app.models.task import AgentTask
from app.models.tutor import CodeReviewRecord, TutorMessage, TutorSession


class ResourceTaskRepository(Protocol):
    async def save_task(self, task: AgentTask) -> None:
        ...

    async def save_resources(self, resources: list[LearningResource]) -> None:
        ...

    async def get_task(self, task_id: str) -> AgentTask | None:
        ...

    async def list_resources(
        self,
        user_id: str | None = None,
        course_id: str | None = None,
        knowledge_point_id: str | None = None,
        resource_type: ResourceType | None = None,
    ) -> list[LearningResource]:
        ...

    async def get_resource(self, resource_id: str) -> LearningResource | None:
        ...

    async def update_resource(self, resource: LearningResource) -> None:
        ...

    async def delete_resource(self, resource_id: str) -> bool:
        ...

    async def save_tutor_session(self, session: TutorSession) -> None:
        ...

    async def save_tutor_messages(self, messages: list[TutorMessage]) -> None:
        ...

    async def get_tutor_session(self, session_id: str) -> TutorSession | None:
        ...

    async def list_tutor_messages(self, session_id: str) -> list[TutorMessage]:
        ...

    async def list_recent_tutor_sessions(
        self,
        user_id: str,
        course_id: str | None = None,
        notebook_id: str | None = None,
        limit: int = 12,
    ) -> list[TutorSession]:
        ...

    async def trim_tutor_history(
        self,
        user_id: str,
        course_id: str | None = None,
        notebook_id: str | None = None,
        keep: int = 12,
    ) -> int:
        ...

    async def delete_tutor_history(
        self,
        user_id: str,
        course_id: str | None = None,
        notebook_id: str | None = None,
        visit_id: str | None = None,
    ) -> int:
        ...

    async def save_code_review_record(self, record: CodeReviewRecord) -> None:
        ...

    async def get_code_review_record(
        self,
        record_id: str,
    ) -> CodeReviewRecord | None:
        ...

    async def save_rag_document(self, document: RAGDocument) -> None:
        ...

    async def get_rag_document(self, document_id: str) -> RAGDocument | None:
        ...

    async def save_rag_chunks(self, chunks: list[RAGChunk]) -> None:
        ...

    async def list_rag_documents(
        self,
        user_id: str | None = None,
        course_id: str | None = None,
        notebook_id: str | None = None,
    ) -> list[RAGDocument]:
        ...

    async def list_rag_chunks(self, document_id: str) -> list[RAGChunk]:
        ...

    async def delete_rag_document(self, document_id: str) -> bool:
        ...

    async def search_rag_chunks(
        self,
        course_id: str,
        query_embedding: list[float],
        document_ids: list[str] | None = None,
        limit: int = 5,
    ) -> list[tuple[RAGChunk, float]]:
        ...

    async def save_content_audit(self, audit: ContentAudit) -> None:
        ...

    async def get_content_audit(self, audit_id: str) -> ContentAudit | None:
        ...

    async def save_classroom_session(self, session: ClassroomSession) -> None:
        ...

    async def save_classroom_scenes(self, scenes: list[ClassroomScene]) -> None:
        ...

    async def get_classroom_session(
        self,
        session_id: str,
    ) -> ClassroomSession | None:
        ...

    async def list_classroom_scenes(
        self,
        session_id: str,
    ) -> list[ClassroomScene]:
        ...

    async def save_classroom_quiz(self, quiz: ClassroomQuizArtifact) -> None:
        ...

    async def get_classroom_quiz(self, quiz_id: str) -> ClassroomQuizArtifact | None:
        ...

    async def list_classroom_quizzes(
        self,
        user_id: str,
        course_id: str,
        notebook_id: str | None = None,
    ) -> list[ClassroomQuizArtifact]:
        ...

    async def delete_classroom_quiz(self, quiz_id: str, user_id: str) -> bool:
        ...

    async def save_classroom_flashcard_set(
        self,
        flashcard_set: ClassroomFlashcardSet,
    ) -> None:
        ...

    async def get_classroom_flashcard_set(
        self,
        flashcard_set_id: str,
    ) -> ClassroomFlashcardSet | None:
        ...

    async def list_classroom_flashcard_sets(
        self,
        user_id: str,
        course_id: str,
        notebook_id: str | None = None,
    ) -> list[ClassroomFlashcardSet]:
        ...

    async def delete_classroom_flashcard_set(
        self,
        flashcard_set_id: str,
        user_id: str,
    ) -> bool:
        ...

    async def save_flashcard_practice_record(
        self,
        record: FlashcardPracticeRecord,
    ) -> None:
        ...

    async def list_recent_flashcard_practice_records(
        self,
        user_id: str,
        flashcard_set_ids: set[str] | None = None,
        limit: int = 30,
    ) -> list[FlashcardPracticeRecord]:
        ...

    async def trim_flashcard_practice_records(
        self,
        user_id: str,
        flashcard_set_ids: set[str],
        keep: int = 30,
    ) -> int:
        ...

    async def list_flashcard_practice_records(
        self,
        user_id: str,
        flashcard_set_id: str | None = None,
    ) -> list[FlashcardPracticeRecord]:
        ...

    async def save_quiz_practice_record(
        self,
        record: QuizPracticeRecord,
    ) -> None:
        ...

    async def list_recent_quiz_practice_records(
        self,
        user_id: str,
        course_id: str | None = None,
        notebook_id: str | None = None,
        limit: int = 30,
    ) -> list[QuizPracticeRecord]:
        ...

    async def trim_quiz_practice_records(
        self,
        user_id: str,
        course_id: str | None = None,
        notebook_id: str | None = None,
        keep: int = 30,
    ) -> int:
        ...

    async def clear_flashcard_practice_records(
        self,
        user_id: str,
        flashcard_set_id: str,
    ) -> None:
        ...

    async def save_user_profile(self, profile: dict[str, Any]) -> None:
        ...

    async def get_user_profile(
        self,
        user_id: str,
        course_id: str,
        notebook_id: str | None = None,
    ) -> dict[str, Any] | None:
        ...

    async def get_notebook_context(
        self,
        user_id: str,
        course_id: str,
        notebook_id: str | None = None,
    ) -> dict[str, Any] | None:
        ...


class MongoResourceTaskRepository:
    def __init__(self, database: AsyncIOMotorDatabase):
        self._tasks = database["agent_task"]
        self._resources = database["learning_resource"]
        self._tutor_sessions = database["tutor_session"]
        self._tutor_messages = database["tutor_message"]
        self._code_review_records = database["code_review_record"]
        self._rag_documents = database["rag_document"]
        self._rag_chunks = database["rag_chunk"]
        self._content_audits = database["content_audit"]
        self._classroom_sessions = database["classroom_session"]
        self._classroom_scenes = database["classroom_scene"]
        self._classroom_quizzes = database["classroom_quiz"]
        self._classroom_flashcard_sets = database["classroom_flashcard_set"]
        self._flashcard_practice_records = database["flashcard_practice_record"]
        self._quiz_practice_records = database["quiz_practice_record"]
        self._user_profiles = database["user_profile"]
        self._notebooks = database["notebooks"]

    async def save_task(self, task: AgentTask) -> None:
        document = task.model_dump(mode="python")
        await self._tasks.replace_one(
            {"task_id": task.task_id},
            document,
            upsert=True,
        )

    async def save_resources(self, resources: list[LearningResource]) -> None:
        if not resources:
            return

        await self._resources.insert_many(
            [resource.model_dump(mode="python") for resource in resources]
        )

    async def get_task(self, task_id: str) -> AgentTask | None:
        document = await self._tasks.find_one({"task_id": task_id}, {"_id": False})
        if document is None:
            return None
        return AgentTask.model_validate(document)

    async def list_resources(
        self,
        user_id: str | None = None,
        course_id: str | None = None,
        knowledge_point_id: str | None = None,
        resource_type: ResourceType | None = None,
    ) -> list[LearningResource]:
        query: dict[str, str] = {}
        if user_id:
            query["user_id"] = user_id
        if course_id:
            query["course_id"] = course_id
        if knowledge_point_id:
            query["knowledge_point_id"] = knowledge_point_id
        if resource_type:
            query["type"] = resource_type

        cursor = self._resources.find(query, {"_id": False}).sort("created_at", -1)
        return [LearningResource.model_validate(item) async for item in cursor]

    async def get_resource(self, resource_id: str) -> LearningResource | None:
        document = await self._resources.find_one(
            {"resource_id": resource_id},
            {"_id": False},
        )
        if document is None:
            return None
        return LearningResource.model_validate(document)

    async def update_resource(self, resource: LearningResource) -> None:
        await self._resources.replace_one(
            {"resource_id": resource.resource_id},
            resource.model_dump(mode="python"),
            upsert=True,
        )

    async def delete_resource(self, resource_id: str) -> bool:
        result = await self._resources.delete_one({"resource_id": resource_id})
        return result.deleted_count == 1

    async def save_tutor_session(self, session: TutorSession) -> None:
        await self._tutor_sessions.replace_one(
            {"session_id": session.session_id},
            session.model_dump(mode="python"),
            upsert=True,
        )

    async def save_tutor_messages(self, messages: list[TutorMessage]) -> None:
        if not messages:
            return

        await self._tutor_messages.insert_many(
            [message.model_dump(mode="python") for message in messages]
        )

    async def get_tutor_session(self, session_id: str) -> TutorSession | None:
        document = await self._tutor_sessions.find_one(
            {"session_id": session_id},
            {"_id": False},
        )
        if document is None:
            return None
        return TutorSession.model_validate(document)

    async def list_tutor_messages(self, session_id: str) -> list[TutorMessage]:
        cursor = self._tutor_messages.find(
            {"session_id": session_id},
            {"_id": False},
        ).sort("created_at", 1)
        return [TutorMessage.model_validate(item) async for item in cursor]

    async def list_recent_tutor_sessions(
        self,
        user_id: str,
        course_id: str | None = None,
        notebook_id: str | None = None,
        limit: int = 12,
    ) -> list[TutorSession]:
        query = _tutor_scope_query(
            user_id=user_id,
            course_id=course_id,
            notebook_id=notebook_id,
        )
        cursor = (
            self._tutor_sessions.find(query, {"_id": False})
            .sort("updated_at", -1)
            .limit(limit)
        )
        return [TutorSession.model_validate(item) async for item in cursor]

    async def trim_tutor_history(
        self,
        user_id: str,
        course_id: str | None = None,
        notebook_id: str | None = None,
        keep: int = 12,
    ) -> int:
        query = _tutor_scope_query(
            user_id=user_id,
            course_id=course_id,
            notebook_id=notebook_id,
        )
        cursor = (
            self._tutor_sessions.find(query, {"_id": False, "session_id": True})
            .sort("updated_at", -1)
            .skip(keep)
        )
        session_ids = [item["session_id"] async for item in cursor]
        if not session_ids:
            return 0
        await self._tutor_messages.delete_many({"session_id": {"$in": session_ids}})
        result = await self._tutor_sessions.delete_many(
            {"session_id": {"$in": session_ids}}
        )
        return result.deleted_count

    async def delete_tutor_history(
        self,
        user_id: str,
        course_id: str | None = None,
        notebook_id: str | None = None,
        visit_id: str | None = None,
    ) -> int:
        query: dict[str, str] = {"user_id": user_id}
        if course_id:
            query["course_id"] = course_id
        if notebook_id:
            query["notebook_id"] = notebook_id
        if visit_id:
            query["visit_id"] = visit_id

        cursor = self._tutor_sessions.find(query, {"_id": False, "session_id": True})
        session_ids = [item["session_id"] async for item in cursor]
        if not session_ids:
            return 0

        await self._tutor_messages.delete_many({"session_id": {"$in": session_ids}})
        result = await self._tutor_sessions.delete_many(
            {"session_id": {"$in": session_ids}}
        )
        return result.deleted_count

    async def save_code_review_record(self, record: CodeReviewRecord) -> None:
        await self._code_review_records.replace_one(
            {"record_id": record.record_id},
            record.model_dump(mode="python"),
            upsert=True,
        )

    async def get_code_review_record(
        self,
        record_id: str,
    ) -> CodeReviewRecord | None:
        document = await self._code_review_records.find_one(
            {"record_id": record_id},
            {"_id": False},
        )
        if document is None:
            return None
        return CodeReviewRecord.model_validate(document)

    async def save_rag_document(self, document: RAGDocument) -> None:
        await self._rag_documents.replace_one(
            {"document_id": document.document_id},
            document.model_dump(mode="python"),
            upsert=True,
        )

    async def get_rag_document(self, document_id: str) -> RAGDocument | None:
        document = await self._rag_documents.find_one(
            {"document_id": document_id},
            {"_id": False},
        )
        if document is None:
            return None
        return RAGDocument.model_validate(document)

    async def save_rag_chunks(self, chunks: list[RAGChunk]) -> None:
        if not chunks:
            return

        await self._rag_chunks.insert_many(
            [chunk.model_dump(mode="python") for chunk in chunks]
        )

    async def list_rag_documents(
        self,
        user_id: str | None = None,
        course_id: str | None = None,
        notebook_id: str | None = None,
    ) -> list[RAGDocument]:
        query: dict[str, object] = {}
        if user_id:
            query["user_id"] = user_id
        if course_id:
            query["course_id"] = course_id
        if notebook_id:
            query["$or"] = [
                {"notebook_id": notebook_id},
                {"notebook_id": {"$exists": False}, "course_id": notebook_id},
            ]

        cursor = self._rag_documents.find(query, {"_id": False}).sort("created_at", -1)
        return [RAGDocument.model_validate(item) async for item in cursor]

    async def list_rag_chunks(self, document_id: str) -> list[RAGChunk]:
        cursor = self._rag_chunks.find(
            {"document_id": document_id},
            {"_id": False},
        ).sort("chunk_index", 1)
        return [RAGChunk.model_validate(item) async for item in cursor]

    async def delete_rag_document(self, document_id: str) -> bool:
        await self._rag_chunks.delete_many({"document_id": document_id})
        result = await self._rag_documents.delete_one({"document_id": document_id})
        return result.deleted_count > 0

    async def search_rag_chunks(
        self,
        course_id: str,
        query_embedding: list[float],
        document_ids: list[str] | None = None,
        limit: int = 5,
    ) -> list[tuple[RAGChunk, float]]:
        query: dict[str, object] = {"course_id": course_id}
        if document_ids:
            query["document_id"] = {"$in": document_ids}

        cursor = self._rag_chunks.find(query, {"_id": False})
        chunks = [RAGChunk.model_validate(item) async for item in cursor]
        scored = [
            (chunk, _cosine_similarity(query_embedding, chunk.embedding))
            for chunk in chunks
        ]
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:limit]

    async def save_content_audit(self, audit: ContentAudit) -> None:
        await self._content_audits.replace_one(
            {"audit_id": audit.audit_id},
            audit.model_dump(mode="python"),
            upsert=True,
        )

    async def get_content_audit(self, audit_id: str) -> ContentAudit | None:
        document = await self._content_audits.find_one(
            {"audit_id": audit_id},
            {"_id": False},
        )
        if document is None:
            return None
        return ContentAudit.model_validate(document)

    async def save_classroom_session(self, session: ClassroomSession) -> None:
        await self._classroom_sessions.replace_one(
            {"session_id": session.session_id},
            session.model_dump(mode="python"),
            upsert=True,
        )

    async def save_classroom_scenes(self, scenes: list[ClassroomScene]) -> None:
        if not scenes:
            return

        await self._classroom_scenes.insert_many(
            [scene.model_dump(mode="python") for scene in scenes]
        )

    async def get_classroom_session(
        self,
        session_id: str,
    ) -> ClassroomSession | None:
        document = await self._classroom_sessions.find_one(
            {"session_id": session_id},
            {"_id": False},
        )
        if document is None:
            return None
        return ClassroomSession.model_validate(document)

    async def list_classroom_scenes(
        self,
        session_id: str,
    ) -> list[ClassroomScene]:
        cursor = self._classroom_scenes.find(
            {"session_id": session_id},
            {"_id": False},
        ).sort("order", 1)
        return [ClassroomScene.model_validate(item) async for item in cursor]

    async def save_classroom_quiz(self, quiz: ClassroomQuizArtifact) -> None:
        await self._classroom_quizzes.replace_one(
            {"quiz_id": quiz.quiz_id},
            quiz.model_dump(mode="python"),
            upsert=True,
        )

    async def get_classroom_quiz(self, quiz_id: str) -> ClassroomQuizArtifact | None:
        document = await self._classroom_quizzes.find_one(
            {"quiz_id": quiz_id},
            {"_id": False},
        )
        if document is None:
            return None
        return ClassroomQuizArtifact.model_validate(document)

    async def list_classroom_quizzes(
        self,
        user_id: str,
        course_id: str,
        notebook_id: str | None = None,
    ) -> list[ClassroomQuizArtifact]:
        query: dict[str, object] = {"user_id": user_id, "course_id": course_id}
        if notebook_id:
            query["$or"] = [
                {"notebook_id": notebook_id},
                {"notebook_id": {"$exists": False}, "course_id": notebook_id},
            ]
        cursor = self._classroom_quizzes.find(
            query,
            {"_id": False},
        ).sort("created_at", -1)
        return [ClassroomQuizArtifact.model_validate(item) async for item in cursor]

    async def delete_classroom_quiz(self, quiz_id: str, user_id: str) -> bool:
        result = await self._classroom_quizzes.delete_one(
            {"quiz_id": quiz_id, "user_id": user_id}
        )
        if result.deleted_count > 0:
            await self._quiz_practice_records.delete_many(
                {"quiz_id": quiz_id, "user_id": user_id}
            )
            return True
        return False

    async def save_classroom_flashcard_set(
        self,
        flashcard_set: ClassroomFlashcardSet,
    ) -> None:
        await self._classroom_flashcard_sets.replace_one(
            {"flashcard_set_id": flashcard_set.flashcard_set_id},
            flashcard_set.model_dump(mode="python"),
            upsert=True,
        )

    async def get_classroom_flashcard_set(
        self,
        flashcard_set_id: str,
    ) -> ClassroomFlashcardSet | None:
        document = await self._classroom_flashcard_sets.find_one(
            {"flashcard_set_id": flashcard_set_id},
            {"_id": False},
        )
        if document is None:
            return None
        return ClassroomFlashcardSet.model_validate(document)

    async def list_classroom_flashcard_sets(
        self,
        user_id: str,
        course_id: str,
        notebook_id: str | None = None,
    ) -> list[ClassroomFlashcardSet]:
        query: dict[str, object] = {"user_id": user_id, "course_id": course_id}
        if notebook_id:
            query["$or"] = [
                {"notebook_id": notebook_id},
                {"notebook_id": {"$exists": False}, "course_id": notebook_id},
            ]
        cursor = self._classroom_flashcard_sets.find(
            query,
            {"_id": False},
        ).sort("created_at", -1)
        return [ClassroomFlashcardSet.model_validate(item) async for item in cursor]

    async def delete_classroom_flashcard_set(
        self,
        flashcard_set_id: str,
        user_id: str,
    ) -> bool:
        result = await self._classroom_flashcard_sets.delete_one(
            {"flashcard_set_id": flashcard_set_id, "user_id": user_id}
        )
        if result.deleted_count > 0:
            await self._flashcard_practice_records.delete_many(
                {"flashcard_set_id": flashcard_set_id, "user_id": user_id}
            )
            return True
        return False

    async def save_flashcard_practice_record(
        self,
        record: FlashcardPracticeRecord,
    ) -> None:
        await self._flashcard_practice_records.replace_one(
            {
                "user_id": record.user_id,
                "flashcard_set_id": record.flashcard_set_id,
                "attempt_id": record.attempt_id,
                "card_id": record.card_id,
            },
            record.model_dump(mode="python"),
            upsert=True,
        )

    async def list_recent_flashcard_practice_records(
        self,
        user_id: str,
        flashcard_set_ids: set[str] | None = None,
        limit: int = 30,
    ) -> list[FlashcardPracticeRecord]:
        query: dict[str, object] = {"user_id": user_id}
        if flashcard_set_ids is not None:
            query["flashcard_set_id"] = {"$in": list(flashcard_set_ids)}
        cursor = (
            self._flashcard_practice_records.find(query, {"_id": False})
            .sort("updated_at", -1)
            .limit(limit)
        )
        return [FlashcardPracticeRecord.model_validate(item) async for item in cursor]

    async def trim_flashcard_practice_records(
        self,
        user_id: str,
        flashcard_set_ids: set[str],
        keep: int = 30,
    ) -> int:
        if not flashcard_set_ids:
            return 0
        query: dict[str, object] = {
            "user_id": user_id,
            "flashcard_set_id": {"$in": list(flashcard_set_ids)},
        }
        cursor = (
            self._flashcard_practice_records.find(query, {"_id": False, "record_id": True})
            .sort("updated_at", -1)
            .skip(keep)
        )
        record_ids = [item["record_id"] async for item in cursor]
        if not record_ids:
            return 0
        result = await self._flashcard_practice_records.delete_many(
            {"record_id": {"$in": record_ids}}
        )
        return result.deleted_count

    async def list_flashcard_practice_records(
        self,
        user_id: str,
        flashcard_set_id: str | None = None,
    ) -> list[FlashcardPracticeRecord]:
        query = {"user_id": user_id}
        if flashcard_set_id:
            query["flashcard_set_id"] = flashcard_set_id

        cursor = self._flashcard_practice_records.find(
            query,
            {"_id": False},
        ).sort("updated_at", 1)
        return [FlashcardPracticeRecord.model_validate(item) async for item in cursor]

    async def clear_flashcard_practice_records(
        self,
        user_id: str,
        flashcard_set_id: str,
    ) -> None:
        await self._flashcard_practice_records.delete_many(
            {"user_id": user_id, "flashcard_set_id": flashcard_set_id}
        )

    async def save_quiz_practice_record(
        self,
        record: QuizPracticeRecord,
    ) -> None:
        await self._quiz_practice_records.replace_one(
            {
                "user_id": record.user_id,
                "quiz_id": record.quiz_id,
                "question_id": record.question_id,
            },
            record.model_dump(mode="python"),
            upsert=True,
        )

    async def list_recent_quiz_practice_records(
        self,
        user_id: str,
        course_id: str | None = None,
        notebook_id: str | None = None,
        limit: int = 30,
    ) -> list[QuizPracticeRecord]:
        query = _quiz_practice_scope_query(
            user_id=user_id,
            course_id=course_id,
            notebook_id=notebook_id,
        )
        cursor = (
            self._quiz_practice_records.find(query, {"_id": False})
            .sort("updated_at", -1)
            .limit(limit)
        )
        return [QuizPracticeRecord.model_validate(item) async for item in cursor]

    async def trim_quiz_practice_records(
        self,
        user_id: str,
        course_id: str | None = None,
        notebook_id: str | None = None,
        keep: int = 30,
    ) -> int:
        query = _quiz_practice_scope_query(
            user_id=user_id,
            course_id=course_id,
            notebook_id=notebook_id,
        )
        cursor = (
            self._quiz_practice_records.find(query, {"_id": False, "record_id": True})
            .sort("updated_at", -1)
            .skip(keep)
        )
        record_ids = [item["record_id"] async for item in cursor]
        if not record_ids:
            return 0
        result = await self._quiz_practice_records.delete_many(
            {"record_id": {"$in": record_ids}}
        )
        return result.deleted_count

    async def save_user_profile(self, profile: dict[str, Any]) -> None:
        await self._user_profiles.replace_one(
            _profile_scope_query(
                user_id=str(profile.get("user_id") or ""),
                course_id=str(profile.get("course_id") or ""),
                notebook_id=profile.get("notebook_id"),
            ),
            profile,
            upsert=True,
        )

    async def get_user_profile(
        self,
        user_id: str,
        course_id: str,
        notebook_id: str | None = None,
    ) -> dict[str, Any] | None:
        return await self._user_profiles.find_one(
            _profile_scope_query(user_id, course_id, notebook_id),
            {"_id": False},
        )

    async def get_notebook_context(
        self,
        user_id: str,
        course_id: str,
        notebook_id: str | None = None,
    ) -> dict[str, Any] | None:
        lookup_id = notebook_id or course_id
        document = await self._notebooks.find_one(
            {"user_id": user_id, "notebook_id": lookup_id},
            {"_id": False},
        )
        if document is not None:
            return document
        return await self._notebooks.find_one(
            {"user_id": user_id, "course_id": course_id},
            {"_id": False},
        )


class InMemoryResourceTaskRepository:
    def __init__(self):
        self._tasks: dict[str, AgentTask] = {}
        self._resources: dict[str, LearningResource] = {}
        self._tutor_sessions: dict[str, TutorSession] = {}
        self._tutor_messages: dict[str, TutorMessage] = {}
        self._code_review_records: dict[str, CodeReviewRecord] = {}
        self._rag_documents: dict[str, RAGDocument] = {}
        self._rag_chunks: dict[str, RAGChunk] = {}
        self._content_audits: dict[str, ContentAudit] = {}
        self._classroom_sessions: dict[str, ClassroomSession] = {}
        self._classroom_scenes: dict[str, ClassroomScene] = {}
        self._classroom_quizzes: dict[str, ClassroomQuizArtifact] = {}
        self._classroom_flashcard_sets: dict[str, ClassroomFlashcardSet] = {}
        self._flashcard_practice_records: dict[str, FlashcardPracticeRecord] = {}
        self._quiz_practice_records: dict[str, QuizPracticeRecord] = {}
        self._user_profiles: dict[str, dict[str, Any]] = {}
        self._notebooks: dict[str, dict[str, Any]] = {}

    async def save_task(self, task: AgentTask) -> None:
        self._tasks[task.task_id] = task.model_copy(deep=True)

    async def save_resources(self, resources: list[LearningResource]) -> None:
        for resource in resources:
            self._resources[resource.resource_id] = resource.model_copy(deep=True)

    async def get_task(self, task_id: str) -> AgentTask | None:
        task = self._tasks.get(task_id)
        return task.model_copy(deep=True) if task else None

    async def list_resources(
        self,
        user_id: str | None = None,
        course_id: str | None = None,
        knowledge_point_id: str | None = None,
        resource_type: ResourceType | None = None,
    ) -> list[LearningResource]:
        resources = list(self._resources.values())
        if user_id:
            resources = [item for item in resources if item.user_id == user_id]
        if course_id:
            resources = [item for item in resources if item.course_id == course_id]
        if knowledge_point_id:
            resources = [
                item for item in resources if item.knowledge_point_id == knowledge_point_id
            ]
        if resource_type:
            resources = [item for item in resources if item.type == resource_type]

        resources.sort(key=lambda item: item.created_at, reverse=True)
        return [resource.model_copy(deep=True) for resource in resources]

    async def get_resource(self, resource_id: str) -> LearningResource | None:
        resource = self._resources.get(resource_id)
        return resource.model_copy(deep=True) if resource else None

    async def update_resource(self, resource: LearningResource) -> None:
        self._resources[resource.resource_id] = resource.model_copy(deep=True)

    async def delete_resource(self, resource_id: str) -> bool:
        if resource_id not in self._resources:
            return False
        del self._resources[resource_id]
        return True

    async def save_tutor_session(self, session: TutorSession) -> None:
        self._tutor_sessions[session.session_id] = session.model_copy(deep=True)

    async def save_tutor_messages(self, messages: list[TutorMessage]) -> None:
        for message in messages:
            self._tutor_messages[message.message_id] = message.model_copy(deep=True)

    async def get_tutor_session(self, session_id: str) -> TutorSession | None:
        session = self._tutor_sessions.get(session_id)
        return session.model_copy(deep=True) if session else None

    async def list_tutor_messages(self, session_id: str) -> list[TutorMessage]:
        messages = [
            item
            for item in self._tutor_messages.values()
            if item.session_id == session_id
        ]
        messages.sort(key=lambda item: item.created_at)
        return [message.model_copy(deep=True) for message in messages]

    async def list_recent_tutor_sessions(
        self,
        user_id: str,
        course_id: str | None = None,
        notebook_id: str | None = None,
        limit: int = 12,
    ) -> list[TutorSession]:
        sessions = [
            item
            for item in self._tutor_sessions.values()
            if _matches_tutor_scope(item, user_id, course_id, notebook_id)
        ]
        sessions.sort(key=lambda item: item.updated_at, reverse=True)
        return [session.model_copy(deep=True) for session in sessions[:limit]]

    async def trim_tutor_history(
        self,
        user_id: str,
        course_id: str | None = None,
        notebook_id: str | None = None,
        keep: int = 12,
    ) -> int:
        sessions = [
            item
            for item in self._tutor_sessions.values()
            if _matches_tutor_scope(item, user_id, course_id, notebook_id)
        ]
        sessions.sort(key=lambda item: item.updated_at, reverse=True)
        stale_session_ids = {session.session_id for session in sessions[keep:]}
        if not stale_session_ids:
            return 0
        for session_id in stale_session_ids:
            del self._tutor_sessions[session_id]
        stale_message_ids = [
            message_id
            for message_id, message in self._tutor_messages.items()
            if message.session_id in stale_session_ids
        ]
        for message_id in stale_message_ids:
            del self._tutor_messages[message_id]
        return len(stale_session_ids)

    async def delete_tutor_history(
        self,
        user_id: str,
        course_id: str | None = None,
        notebook_id: str | None = None,
        visit_id: str | None = None,
    ) -> int:
        session_ids = [
            session_id
            for session_id, session in self._tutor_sessions.items()
            if session.user_id == user_id
            and (course_id is None or session.course_id == course_id)
            and (notebook_id is None or session.notebook_id == notebook_id)
            and (visit_id is None or session.visit_id == visit_id)
        ]
        if not session_ids:
            return 0

        selected = set(session_ids)
        for session_id in session_ids:
            del self._tutor_sessions[session_id]
        message_ids = [
            message_id
            for message_id, message in self._tutor_messages.items()
            if message.session_id in selected
        ]
        for message_id in message_ids:
            del self._tutor_messages[message_id]
        return len(session_ids)

    async def save_code_review_record(self, record: CodeReviewRecord) -> None:
        self._code_review_records[record.record_id] = record.model_copy(deep=True)

    async def get_code_review_record(
        self,
        record_id: str,
    ) -> CodeReviewRecord | None:
        record = self._code_review_records.get(record_id)
        return record.model_copy(deep=True) if record else None

    async def save_rag_document(self, document: RAGDocument) -> None:
        self._rag_documents[document.document_id] = document.model_copy(deep=True)

    async def get_rag_document(self, document_id: str) -> RAGDocument | None:
        document = self._rag_documents.get(document_id)
        return document.model_copy(deep=True) if document else None

    async def save_rag_chunks(self, chunks: list[RAGChunk]) -> None:
        for chunk in chunks:
            self._rag_chunks[chunk.chunk_id] = chunk.model_copy(deep=True)

    async def list_rag_documents(
        self,
        user_id: str | None = None,
        course_id: str | None = None,
        notebook_id: str | None = None,
    ) -> list[RAGDocument]:
        documents = list(self._rag_documents.values())
        if user_id:
            documents = [item for item in documents if item.user_id == user_id]
        if course_id:
            documents = [item for item in documents if item.course_id == course_id]
        if notebook_id:
            documents = [
                item
                for item in documents
                if (item.notebook_id or item.course_id) == notebook_id
            ]

        documents.sort(key=lambda item: item.created_at, reverse=True)
        return [document.model_copy(deep=True) for document in documents]

    async def list_rag_chunks(self, document_id: str) -> list[RAGChunk]:
        chunks = [
            item for item in self._rag_chunks.values() if item.document_id == document_id
        ]
        chunks.sort(key=lambda item: item.chunk_index)
        return [chunk.model_copy(deep=True) for chunk in chunks]

    async def delete_rag_document(self, document_id: str) -> bool:
        existed = document_id in self._rag_documents
        self._rag_documents.pop(document_id, None)
        chunk_ids = [
            chunk_id
            for chunk_id, chunk in self._rag_chunks.items()
            if chunk.document_id == document_id
        ]
        for chunk_id in chunk_ids:
            del self._rag_chunks[chunk_id]
        return existed

    async def search_rag_chunks(
        self,
        course_id: str,
        query_embedding: list[float],
        document_ids: list[str] | None = None,
        limit: int = 5,
    ) -> list[tuple[RAGChunk, float]]:
        chunks = [
            item for item in self._rag_chunks.values() if item.course_id == course_id
        ]
        if document_ids:
            selected = set(document_ids)
            chunks = [item for item in chunks if item.document_id in selected]

        scored = [
            (chunk.model_copy(deep=True), _cosine_similarity(query_embedding, chunk.embedding))
            for chunk in chunks
        ]
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:limit]

    async def save_content_audit(self, audit: ContentAudit) -> None:
        self._content_audits[audit.audit_id] = audit.model_copy(deep=True)

    async def get_content_audit(self, audit_id: str) -> ContentAudit | None:
        audit = self._content_audits.get(audit_id)
        return audit.model_copy(deep=True) if audit else None

    async def save_classroom_session(self, session: ClassroomSession) -> None:
        self._classroom_sessions[session.session_id] = session.model_copy(deep=True)

    async def save_classroom_scenes(self, scenes: list[ClassroomScene]) -> None:
        for scene in scenes:
            self._classroom_scenes[scene.scene_id] = scene.model_copy(deep=True)

    async def get_classroom_session(
        self,
        session_id: str,
    ) -> ClassroomSession | None:
        session = self._classroom_sessions.get(session_id)
        return session.model_copy(deep=True) if session else None

    async def list_classroom_scenes(
        self,
        session_id: str,
    ) -> list[ClassroomScene]:
        scenes = [
            item
            for item in self._classroom_scenes.values()
            if item.session_id == session_id
        ]
        scenes.sort(key=lambda item: item.order)
        return [scene.model_copy(deep=True) for scene in scenes]

    async def save_classroom_quiz(self, quiz: ClassroomQuizArtifact) -> None:
        self._classroom_quizzes[quiz.quiz_id] = quiz.model_copy(deep=True)

    async def get_classroom_quiz(self, quiz_id: str) -> ClassroomQuizArtifact | None:
        quiz = self._classroom_quizzes.get(quiz_id)
        return quiz.model_copy(deep=True) if quiz else None

    async def list_classroom_quizzes(
        self,
        user_id: str,
        course_id: str,
        notebook_id: str | None = None,
    ) -> list[ClassroomQuizArtifact]:
        quizzes = [
            item
            for item in self._classroom_quizzes.values()
            if item.user_id == user_id and item.course_id == course_id
            and (
                notebook_id is None
                or (item.notebook_id or item.course_id) == notebook_id
            )
        ]
        quizzes.sort(key=lambda item: item.created_at, reverse=True)
        return [quiz.model_copy(deep=True) for quiz in quizzes]

    async def delete_classroom_quiz(self, quiz_id: str, user_id: str) -> bool:
        quiz = self._classroom_quizzes.get(quiz_id)
        if quiz is None or quiz.user_id != user_id:
            return False
        del self._classroom_quizzes[quiz_id]
        keys = [
            key
            for key, record in self._quiz_practice_records.items()
            if record.quiz_id == quiz_id and record.user_id == user_id
        ]
        for key in keys:
            del self._quiz_practice_records[key]
        return True

    async def save_classroom_flashcard_set(
        self,
        flashcard_set: ClassroomFlashcardSet,
    ) -> None:
        self._classroom_flashcard_sets[flashcard_set.flashcard_set_id] = (
            flashcard_set.model_copy(deep=True)
        )

    async def get_classroom_flashcard_set(
        self,
        flashcard_set_id: str,
    ) -> ClassroomFlashcardSet | None:
        flashcard_set = self._classroom_flashcard_sets.get(flashcard_set_id)
        return flashcard_set.model_copy(deep=True) if flashcard_set else None

    async def list_classroom_flashcard_sets(
        self,
        user_id: str,
        course_id: str,
        notebook_id: str | None = None,
    ) -> list[ClassroomFlashcardSet]:
        flashcard_sets = [
            item
            for item in self._classroom_flashcard_sets.values()
            if item.user_id == user_id and item.course_id == course_id
            and (
                notebook_id is None
                or (item.notebook_id or item.course_id) == notebook_id
            )
        ]
        flashcard_sets.sort(key=lambda item: item.created_at, reverse=True)
        return [flashcard_set.model_copy(deep=True) for flashcard_set in flashcard_sets]

    async def delete_classroom_flashcard_set(
        self,
        flashcard_set_id: str,
        user_id: str,
    ) -> bool:
        flashcard_set = self._classroom_flashcard_sets.get(flashcard_set_id)
        if flashcard_set is None or flashcard_set.user_id != user_id:
            return False
        del self._classroom_flashcard_sets[flashcard_set_id]
        await self.clear_flashcard_practice_records(
            user_id=user_id,
            flashcard_set_id=flashcard_set_id,
        )
        return True

    async def save_flashcard_practice_record(
        self,
        record: FlashcardPracticeRecord,
    ) -> None:
        key = (
            f"{record.user_id}:{record.flashcard_set_id}:"
            f"{record.attempt_id}:{record.card_id}"
        )
        self._flashcard_practice_records[key] = record.model_copy(deep=True)

    async def list_recent_flashcard_practice_records(
        self,
        user_id: str,
        flashcard_set_ids: set[str] | None = None,
        limit: int = 30,
    ) -> list[FlashcardPracticeRecord]:
        records = [
            item
            for item in self._flashcard_practice_records.values()
            if item.user_id == user_id
            and (
                flashcard_set_ids is None
                or item.flashcard_set_id in flashcard_set_ids
            )
        ]
        records.sort(key=lambda item: item.updated_at, reverse=True)
        return [record.model_copy(deep=True) for record in records[:limit]]

    async def trim_flashcard_practice_records(
        self,
        user_id: str,
        flashcard_set_ids: set[str],
        keep: int = 30,
    ) -> int:
        records = [
            item
            for item in self._flashcard_practice_records.values()
            if item.user_id == user_id and item.flashcard_set_id in flashcard_set_ids
        ]
        records.sort(key=lambda item: item.updated_at, reverse=True)
        stale_ids = {record.record_id for record in records[keep:]}
        if not stale_ids:
            return 0
        keys = [
            key
            for key, record in self._flashcard_practice_records.items()
            if record.record_id in stale_ids
        ]
        for key in keys:
            del self._flashcard_practice_records[key]
        return len(keys)

    async def list_flashcard_practice_records(
        self,
        user_id: str,
        flashcard_set_id: str | None = None,
    ) -> list[FlashcardPracticeRecord]:
        records = [
            item
            for item in self._flashcard_practice_records.values()
            if item.user_id == user_id
            and (flashcard_set_id is None or item.flashcard_set_id == flashcard_set_id)
        ]
        records.sort(key=lambda item: item.updated_at)
        return [record.model_copy(deep=True) for record in records]

    async def clear_flashcard_practice_records(
        self,
        user_id: str,
        flashcard_set_id: str,
    ) -> None:
        keys = [
            key
            for key, record in self._flashcard_practice_records.items()
            if record.user_id == user_id and record.flashcard_set_id == flashcard_set_id
        ]
        for key in keys:
            del self._flashcard_practice_records[key]

    async def save_quiz_practice_record(
        self,
        record: QuizPracticeRecord,
    ) -> None:
        key = f"{record.user_id}:{record.quiz_id}:{record.question_id}"
        self._quiz_practice_records[key] = record.model_copy(deep=True)

    async def list_recent_quiz_practice_records(
        self,
        user_id: str,
        course_id: str | None = None,
        notebook_id: str | None = None,
        limit: int = 30,
    ) -> list[QuizPracticeRecord]:
        records = [
            item
            for item in self._quiz_practice_records.values()
            if _matches_quiz_practice_scope(item, user_id, course_id, notebook_id)
        ]
        records.sort(key=lambda item: item.updated_at, reverse=True)
        return [record.model_copy(deep=True) for record in records[:limit]]

    async def trim_quiz_practice_records(
        self,
        user_id: str,
        course_id: str | None = None,
        notebook_id: str | None = None,
        keep: int = 30,
    ) -> int:
        records = [
            item
            for item in self._quiz_practice_records.values()
            if _matches_quiz_practice_scope(item, user_id, course_id, notebook_id)
        ]
        records.sort(key=lambda item: item.updated_at, reverse=True)
        stale_ids = {record.record_id for record in records[keep:]}
        if not stale_ids:
            return 0
        keys = [
            key
            for key, record in self._quiz_practice_records.items()
            if record.record_id in stale_ids
        ]
        for key in keys:
            del self._quiz_practice_records[key]
        return len(keys)

    async def save_user_profile(self, profile: dict[str, Any]) -> None:
        key = _profile_key(
            user_id=str(profile.get("user_id") or ""),
            course_id=str(profile.get("course_id") or ""),
            notebook_id=profile.get("notebook_id"),
        )
        self._user_profiles[key] = profile.copy()

    async def get_user_profile(
        self,
        user_id: str,
        course_id: str,
        notebook_id: str | None = None,
    ) -> dict[str, Any] | None:
        profile = self._user_profiles.get(_profile_key(user_id, course_id, notebook_id))
        return profile.copy() if profile else None

    async def get_notebook_context(
        self,
        user_id: str,
        course_id: str,
        notebook_id: str | None = None,
    ) -> dict[str, Any] | None:
        lookup_id = notebook_id or course_id
        for notebook in self._notebooks.values():
            if notebook.get("user_id") != user_id:
                continue
            if notebook.get("notebook_id") == lookup_id:
                return notebook.copy()
            if notebook.get("course_id") == course_id:
                return notebook.copy()
        return None


def _tutor_scope_query(
    user_id: str,
    course_id: str | None = None,
    notebook_id: str | None = None,
) -> dict[str, object]:
    query: dict[str, object] = {"user_id": user_id}
    if notebook_id:
        query["notebook_id"] = notebook_id
    elif course_id:
        query["course_id"] = course_id
    return query


def _profile_scope_query(
    user_id: str,
    course_id: str,
    notebook_id: str | None = None,
) -> dict[str, object]:
    return {
        "user_id": user_id,
        "course_id": course_id,
        "notebook_id": notebook_id,
    }


def _profile_key(
    user_id: str,
    course_id: str,
    notebook_id: str | None = None,
) -> str:
    return f"{user_id}:{course_id}:{notebook_id or ''}"


def _quiz_practice_scope_query(
    user_id: str,
    course_id: str | None = None,
    notebook_id: str | None = None,
) -> dict[str, object]:
    query: dict[str, object] = {"user_id": user_id}
    if notebook_id:
        query["notebook_id"] = notebook_id
    elif course_id:
        query["course_id"] = course_id
    return query


def _matches_tutor_scope(
    session: TutorSession,
    user_id: str,
    course_id: str | None = None,
    notebook_id: str | None = None,
) -> bool:
    if session.user_id != user_id:
        return False
    if notebook_id:
        return session.notebook_id == notebook_id
    if course_id:
        return session.course_id == course_id
    return True


def _matches_quiz_practice_scope(
    record: QuizPracticeRecord,
    user_id: str,
    course_id: str | None = None,
    notebook_id: str | None = None,
) -> bool:
    if record.user_id != user_id:
        return False
    if notebook_id:
        return record.notebook_id == notebook_id
    if course_id:
        return record.course_id == course_id
    return True


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0

    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = sqrt(sum(value * value for value in left))
    right_norm = sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)
