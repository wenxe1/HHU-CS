import sys
import unittest
from pathlib import Path
from uuid import uuid4

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ServerSelectionTimeoutError

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.db.repositories import MongoResourceTaskRepository
from app.schemas.audit import AuditResourceRequest
from app.schemas.classroom import ClassroomGenerateRequest
from app.schemas.rag import RAGUploadRequest
from app.schemas.resource import GenerateResourceRequest
from app.schemas.tutor import CodeReviewRequest, TutorAskRequest
from app.services.audit_service import AuditService
from app.services.classroom_service import ClassroomService
from app.services.code_review_service import CodeReviewService
from app.services.rag_service import RAGService
from app.services.resource_service import ResourceGenerateService
from app.services.tutor_service import TutorService
from fakes import FakeAIClient


class MongoRepositoryIntegrationTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.database_name = f"eduagent_studio_test_{uuid4().hex}"
        self.client = AsyncIOMotorClient(
            "mongodb://localhost:27017",
            serverSelectionTimeoutMS=1000,
        )
        try:
            await self.client.admin.command("ping")
        except ServerSelectionTimeoutError as exc:
            self.client.close()
            raise unittest.SkipTest("MongoDB is not running on localhost:27017") from exc

        self.database = self.client[self.database_name]
        self.repository = MongoResourceTaskRepository(self.database)
        self.ai_client = FakeAIClient()

    async def asyncTearDown(self):
        await self.client.drop_database(self.database_name)
        self.client.close()

    async def test_repository_persists_task_and_resource_documents(self):
        service = ResourceGenerateService(self.repository, self.ai_client)

        result = await service.generate(
            GenerateResourceRequest(
                user_id="student-mongo",
                course_id="course-ds",
                knowledge_point_id="kp-stack",
                resource_types=["lecture", "code_lab"],
            )
        )

        task = await self.repository.get_task(result["task_id"])
        self.assertIsNotNone(task)
        self.assertEqual(task.status, "completed")
        self.assertEqual(len(task.resource_ids), 2)

        resources = await self.repository.list_resources(user_id="student-mongo")
        self.assertEqual(len(resources), 2)
        self.assertEqual({item.type for item in resources}, {"lecture", "code_lab"})

        deleted = await self.repository.delete_resource(resources[0].resource_id)
        self.assertTrue(deleted)

    async def test_repository_persists_tutor_and_code_review_documents(self):
        tutor_service = TutorService(self.repository, self.ai_client)
        code_review_service = CodeReviewService(self.repository, self.ai_client)

        tutor_result = await tutor_service.ask(
            TutorAskRequest(
                user_id="student-mongo",
                course_id="course-ds",
                knowledge_point_id="kp-queue",
                question="队列为什么适合 BFS？",
            )
        )
        session = await self.repository.get_tutor_session(tutor_result["session_id"])
        messages = await self.repository.list_tutor_messages(tutor_result["session_id"])
        self.assertIsNotNone(session)
        self.assertEqual(len(messages), 2)

        review_result = await code_review_service.review(
            CodeReviewRequest(
                user_id="student-mongo",
                language="python",
                code="for i in range(3)\n    print(i)",
            )
        )
        record = await self.repository.get_code_review_record(
            review_result["record_id"]
        )
        self.assertIsNotNone(record)
        self.assertEqual(record.issues[0].category, "syntax_error")

    async def test_repository_persists_rag_audit_and_classroom_documents(self):
        rag_service = RAGService(self.repository, self.ai_client)
        resource_service = ResourceGenerateService(self.repository, self.ai_client)
        audit_service = AuditService(self.repository, self.ai_client)
        classroom_service = ClassroomService(self.repository, self.ai_client)

        upload_result = await rag_service.upload(
            RAGUploadRequest(
                user_id="teacher-mongo",
                course_id="course-ds",
                filename="queue.md",
                content="队列适合记录先进先出的搜索顺序。",
            )
        )
        documents = await self.repository.list_rag_documents(course_id="course-ds")
        chunks = await self.repository.list_rag_chunks(upload_result["document_id"])
        self.assertEqual(len(documents), 1)
        self.assertEqual(len(chunks), 1)

        generate_result = await resource_service.generate(
            GenerateResourceRequest(
                user_id="student-mongo",
                course_id="course-ds",
                knowledge_point_id="kp-queue",
                resource_types=["lecture"],
            )
        )
        audit_result = await audit_service.audit_resource(
            generate_result["resource_ids"][0],
            AuditResourceRequest(auditor_id="teacher-mongo"),
        )
        audit = await self.repository.get_content_audit(audit_result["audit_id"])
        resource = await self.repository.get_resource(generate_result["resource_ids"][0])
        self.assertIsNotNone(audit)
        self.assertEqual(resource.audit_status, "approved")

        classroom_result = await classroom_service.generate(
            ClassroomGenerateRequest(
                user_id="student-mongo",
                course_id="course-ds",
                knowledge_point_id="kp-queue",
                topic="队列",
            )
        )
        session = await self.repository.get_classroom_session(
            classroom_result["session_id"]
        )
        scenes = await self.repository.list_classroom_scenes(
            classroom_result["session_id"]
        )
        self.assertIsNotNone(session)
        self.assertGreaterEqual(len(scenes), 6)
