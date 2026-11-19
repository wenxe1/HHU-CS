import asyncio
import sys
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_audit_service,
    get_classroom_service,
    get_rag_service,
    get_resource_generate_service,
)
from app.db.repositories import InMemoryResourceTaskRepository
from app.main import app
from app.models.classroom import (
    ClassroomFlashcardSet,
    ClassroomQuizArtifact,
    FlashcardPracticeRecord,
    QuizPracticeRecord,
)
from app.models.tutor import TutorMessage, TutorSession
from app.schemas.rag import RAGUploadRequest
from app.services import classroom_service as classroom_service_module
from app.services.audit_service import AuditService
from app.services.classroom_service import ClassroomService
from app.services.rag_service import RAGService
from app.services.resource_service import ResourceGenerateService
from fakes import FakeAIClient


class LengthLimitedEmbeddingClient(FakeAIClient):
    def __init__(self, max_chars: int):
        self.max_chars = max_chars
        self.seen_lengths: list[int] = []

    async def embed_texts(self, texts, embedding_domain: str = "para"):
        self.seen_lengths.extend(len(text) for text in texts)
        too_long = [length for length in self.seen_lengths if length > self.max_chars]
        if too_long:
            raise RuntimeError("HTTP Error 400: Bad Request")
        return await super().embed_texts(texts, embedding_domain)


class FailingEmbeddingClient(FakeAIClient):
    async def embed_texts(self, texts, embedding_domain: str = "para"):
        raise RuntimeError("embedding call failed")


class ManyStudyItemsAIClient(FakeAIClient):
    async def generate_json(
        self,
        agent_name,
        system_prompt,
        user_prompt,
        response_schema,
        use_reasoning=False,
    ):
        if agent_name == "Quiz Agent":
            return {
                "title": "Large quiz",
                "questions": [
                    {
                        "question_id": f"q{index}",
                        "type": "single_choice",
                        "stem": f"Question {index}",
                        "options": ["A", "B", "C", "D"],
                        "answer": "A",
                        "explanation": "A is grounded in the source.",
                        "option_explanations": {
                            "A": "A matches the source.",
                            "B": "B does not match the source.",
                            "C": "C does not match the source.",
                            "D": "D does not match the source.",
                        },
                    }
                    for index in range(1, 16)
                ],
            }
        if agent_name == "Flashcard Agent":
            return {
                "title": "Large flashcards",
                "cards": [
                    {
                        "card_id": f"card{index}",
                        "front": f"Term {index}",
                        "back": f"Answer {index}",
                    }
                    for index in range(1, 16)
                ],
            }
        return await super().generate_json(
            agent_name,
            system_prompt,
            user_prompt,
            response_schema,
            use_reasoning,
        )


class InvalidUserProfileAIClient(FakeAIClient):
    async def generate_json(
        self,
        agent_name,
        system_prompt,
        user_prompt,
        response_schema,
        use_reasoning=False,
    ):
        if agent_name == "User Profile Agent":
            return {
                "summary": "AI only returned one radar axis.",
                "radar": [
                    {
                        "key": "conceptual_understanding",
                        "label": "概念理解",
                        "score": 70,
                        "reason": "Only this axis was returned.",
                    }
                ],
                "learning_traits": ["主动提问"],
                "strengths": ["能提出问题"],
                "risks": ["AI 缺少部分雷达轴"],
                "recommendations": [
                    {
                        "title": "补齐练习",
                        "detail": "继续通过测验和闪卡补充学习证据。",
                        "priority": "medium",
                    }
                ],
                "learning_resources": [],
            }
        return await super().generate_json(
            agent_name,
            system_prompt,
            user_prompt,
            response_schema,
            use_reasoning,
        )


class CountingUserProfileAIClient(FakeAIClient):
    def __init__(self):
        self.profile_call_count = 0

    async def generate_json(
        self,
        agent_name,
        system_prompt,
        user_prompt,
        response_schema,
        use_reasoning=False,
    ):
        if agent_name == "User Profile Agent":
            self.profile_call_count += 1
        return await super().generate_json(
            agent_name,
            system_prompt,
            user_prompt,
            response_schema,
            use_reasoning,
        )


class SlowUserProfileAIClient(FakeAIClient):
    async def generate_json(
        self,
        agent_name,
        system_prompt,
        user_prompt,
        response_schema,
        use_reasoning=False,
    ):
        if agent_name == "User Profile Agent":
            await asyncio.sleep(10)
        return await super().generate_json(
            agent_name,
            system_prompt,
            user_prompt,
            response_schema,
            use_reasoning,
        )


class MixedLearningResourceAIClient(FakeAIClient):
    async def generate_json(
        self,
        agent_name,
        system_prompt,
        user_prompt,
        response_schema,
        use_reasoning=False,
    ):
        if agent_name == "User Profile Agent":
            payload = await super().generate_json(
                agent_name,
                system_prompt,
                user_prompt,
                response_schema,
                use_reasoning,
            )
            payload["learning_resources"] = [
                {
                    "title": "MOOC concrete course",
                    "url": "https://www.icourse163.org/course/ZJU-93001",
                    "language": "zh",
                    "reason": "Concrete MOOC course page.",
                },
                {
                    "title": "Bilibili concrete video",
                    "url": "https://www.bilibili.com/video/BV1b7411N798/",
                    "language": "zh",
                    "reason": "Concrete Bilibili video page.",
                },
                {
                    "title": "MOOC homepage",
                    "url": "https://www.icourse163.org/",
                    "language": "zh",
                    "reason": "Homepage should be filtered.",
                },
                {
                    "title": "Bilibili search",
                    "url": "https://search.bilibili.com/all?keyword=computer",
                    "language": "zh",
                    "reason": "Search page should be filtered.",
                },
                {
                    "title": "Unknown Bilibili video",
                    "url": "https://www.bilibili.com/video/BV0000000000/",
                    "language": "zh",
                    "reason": "Unverified video page should be filtered.",
                },
                {
                    "title": "Missing resource",
                    "url": "https://example.com/not-found-404",
                    "language": "en",
                    "reason": "Unknown resource should be filtered.",
                },
            ]
            return payload
        return await super().generate_json(
            agent_name,
            system_prompt,
            user_prompt,
            response_schema,
            use_reasoning,
        )


class D7D8ApiTest(unittest.TestCase):
    def setUp(self):
        self.repository = InMemoryResourceTaskRepository()
        self.ai_client = FakeAIClient()
        app.dependency_overrides[get_resource_generate_service] = (
            lambda: ResourceGenerateService(self.repository, self.ai_client)
        )
        app.dependency_overrides[get_rag_service] = lambda: RAGService(
            self.repository,
            self.ai_client,
        )
        app.dependency_overrides[get_audit_service] = lambda: AuditService(
            self.repository,
            self.ai_client,
        )
        app.dependency_overrides[get_classroom_service] = lambda: ClassroomService(
            self.repository,
            self.ai_client,
        )
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_rag_upload_and_list_documents(self):
        response = self.client.post(
            "/api/rag/upload",
            json={
                "user_id": "teacher-001",
                "course_id": "course-ds",
                "filename": "bfs-notes.md",
                "content": "BFS 使用队列逐层扩展节点。\n\n需要记录 visited 避免重复访问。",
                "metadata": {"chapter": "graph"},
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertGreaterEqual(data["chunk_count"], 1)

        list_response = self.client.get(
            "/api/rag/documents",
            params={"course_id": "course-ds"},
        )
        self.assertEqual(list_response.status_code, 200)
        items = list_response.json()["data"]["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["filename"], "bfs-notes.md")

        rename_response = self.client.patch(
            f"/api/rag/documents/{data['document_id']}",
            json={"source_title": "renamed-bfs-notes.md"},
        )
        self.assertEqual(rename_response.status_code, 200)
        self.assertEqual(
            rename_response.json()["data"]["source_title"],
            "renamed-bfs-notes.md",
        )
        renamed_document = asyncio.run(
            self.repository.get_rag_document(data["document_id"])
        )
        self.assertIsNotNone(renamed_document)
        self.assertEqual(renamed_document.source_title, "renamed-bfs-notes.md")

        delete_response = self.client.delete(
            f"/api/rag/documents/{data['document_id']}",
        )
        self.assertEqual(delete_response.status_code, 200)
        self.assertTrue(delete_response.json()["data"]["deleted"])

        list_after_delete_response = self.client.get(
            "/api/rag/documents",
            params={"course_id": "course-ds"},
        )
        self.assertEqual(list_after_delete_response.json()["data"]["items"], [])

    def test_rag_upload_splits_single_long_paragraph_before_embedding(self):
        ai_client = LengthLimitedEmbeddingClient(max_chars=500)
        service = RAGService(self.repository, ai_client)
        content = "BFS uses a queue and expands graph nodes by layers. " * 40

        result = asyncio.run(
            service.upload(
                RAGUploadRequest(
                    user_id="teacher-long",
                    course_id="course-ds",
                    filename="long-word-extract.txt",
                    content=content,
                )
            )
        )

        self.assertEqual(result["upload_status"], "success")
        self.assertGreater(result["chunk_count"], 1)
        self.assertTrue(ai_client.seen_lengths)
        self.assertLessEqual(max(ai_client.seen_lengths), 500)

    def test_failed_file_processing_removes_rag_document(self):
        service = RAGService(self.repository, FailingEmbeddingClient())
        document = asyncio.run(
            service.create_file_source(
                user_id="student-failed",
                course_id="course-ds",
                notebook_id="course-ds",
                filename="bad-notes.md",
                content_type="text/markdown",
                content_size=42,
                source_type="course_material",
            )
        )

        chunks = asyncio.run(
            service.process_file_source(
                document,
                b"BFS uses a queue and expands graph nodes by layers.",
            )
        )
        documents = asyncio.run(
            self.repository.list_rag_documents(
                user_id="student-failed",
                course_id="course-ds",
                notebook_id="course-ds",
            )
        )
        stored_chunks = asyncio.run(
            self.repository.list_rag_chunks(document.document_id)
        )

        self.assertEqual(chunks, [])
        self.assertEqual(documents, [])
        self.assertEqual(stored_chunks, [])

    def test_classroom_study_generation_is_capped_at_ten_items(self):
        self.ai_client = ManyStudyItemsAIClient()
        rag_service = RAGService(self.repository, self.ai_client)
        content = "\n\n".join(
            f"Section {index}. " + ("BFS expands nodes by layers. " * 16)
            for index in range(12)
        )
        document = asyncio.run(
            rag_service.upload(
                RAGUploadRequest(
                    user_id="student-cap",
                    course_id="course-ds",
                    notebook_id="course-ds",
                    filename="large-bfs.md",
                    content=content,
                )
            )
        )

        quiz_response = self.client.post(
            "/api/classroom/quiz/generate",
            json={
                "user_id": "student-cap",
                "course_id": "course-ds",
                "source_document_ids": [document["document_id"]],
            },
        )
        flashcards_response = self.client.post(
            "/api/classroom/flashcards/generate",
            json={
                "user_id": "student-cap",
                "course_id": "course-ds",
                "source_document_ids": [document["document_id"]],
            },
        )

        self.assertEqual(quiz_response.status_code, 200)
        self.assertEqual(flashcards_response.status_code, 200)
        self.assertEqual(len(quiz_response.json()["data"]["questions"]), 10)
        flashcards = flashcards_response.json()["data"]
        self.assertEqual(len(flashcards["cards"]), 10)

        study_card_ids = [card["card_id"] for card in flashcards["cards"]]
        for index, card_id in enumerate(study_card_ids):
            practice_response = self.client.post(
                "/api/classroom/flashcards/practice",
                json={
                    "user_id": "student-cap",
                    "course_id": "course-ds",
                    "flashcard_set_id": flashcards["flashcard_set_id"],
                    "attempt_id": "attempt-completion",
                    "study_card_ids": study_card_ids,
                    "card_id": card_id,
                    "result": "correct" if index % 2 == 0 else "incorrect",
                },
            )
            self.assertEqual(practice_response.status_code, 200)
            self.assertEqual(
                practice_response.json()["data"]["attempt_completed"],
                index == len(study_card_ids) - 1,
            )

        review_card_ids = [study_card_ids[1], study_card_ids[3]]
        for index, card_id in enumerate(review_card_ids):
            review_response = self.client.post(
                "/api/classroom/flashcards/practice",
                json={
                    "user_id": "student-cap",
                    "course_id": "course-ds",
                    "flashcard_set_id": flashcards["flashcard_set_id"],
                    "attempt_id": "attempt-incorrect-review",
                    "study_card_ids": review_card_ids,
                    "card_id": card_id,
                    "result": "correct",
                },
            )
            self.assertEqual(
                review_response.json()["data"]["attempt_completed"],
                index == len(review_card_ids) - 1,
            )

        oversized_quiz_response = self.client.post(
            "/api/classroom/quiz/generate",
            json={
                "user_id": "student-cap",
                "course_id": "course-ds",
                "source_document_ids": [document["document_id"]],
                "question_count": 11,
            },
        )
        oversized_flashcards_response = self.client.post(
            "/api/classroom/flashcards/generate",
            json={
                "user_id": "student-cap",
                "course_id": "course-ds",
                "source_document_ids": [document["document_id"]],
                "card_count": 11,
            },
        )
        self.assertEqual(oversized_quiz_response.status_code, 422)
        self.assertEqual(oversized_flashcards_response.status_code, 422)

    def test_audit_resource_updates_status_and_persists_audit(self):
        self.client.post(
            "/api/rag/upload",
            json={
                "user_id": "teacher-002",
                "course_id": "course-ds",
                "filename": "graph-search.md",
                "content": "图搜索需要说明状态、边界和复杂度。",
            },
        )
        generate_response = self.client.post(
            "/api/resource/generate",
            json={
                "user_id": "student-201",
                "course_id": "course-ds",
                "knowledge_point_id": "kp-bfs",
                "resource_types": ["lecture"],
            },
        )
        resource_id = generate_response.json()["data"]["resource_ids"][0]

        audit_response = self.client.post(
            f"/api/audit/resource/{resource_id}",
            json={"auditor_id": "teacher-002"},
        )

        self.assertEqual(audit_response.status_code, 200)
        audit = audit_response.json()["data"]
        self.assertEqual(audit["resource_id"], resource_id)
        self.assertEqual(audit["status"], "approved")
        self.assertEqual(audit["risk_level"], "low")
        self.assertEqual(audit["citations"][0]["source_type"], "rag_document")

        detail_response = self.client.get(f"/api/resource/{resource_id}")
        self.assertEqual(detail_response.json()["data"]["audit_status"], "approved")

        audit_record = asyncio.run(
            self.repository.get_content_audit(audit["audit_id"])
        )
        self.assertIsNotNone(audit_record)

    def test_classroom_generate_and_get_detail(self):
        response = self.client.post(
            "/api/classroom/generate",
            json={
                "user_id": "student-301",
                "course_id": "course-ds",
                "knowledge_point_id": "kp-bfs",
                "topic": "BFS 广度优先搜索",
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["status"], "completed")
        self.assertIn("teacher_explain", data["scene_types"])
        self.assertIn("classmate_question", data["scene_types"])
        self.assertIn("whiteboard", data["scene_types"])
        self.assertIn("quiz", data["scene_types"])

        detail_response = self.client.get(f"/api/classroom/{data['session_id']}")
        self.assertEqual(detail_response.status_code, 200)
        detail = detail_response.json()["data"]
        self.assertEqual(detail["title"], "BFS 广度优先搜索 互动课堂")
        self.assertEqual(len(detail["scenes"]), data["scene_count"])
        self.assertEqual(detail["scenes"][0]["speaker"], "AI 教师")


    def test_user_profile_locks_without_data_and_uses_recent_windows(self):
        locked_response = self.client.post(
            "/api/classroom/profile/generate",
            json={
                "user_id": "profile-empty",
                "course_id": "course-ds",
                "notebook_id": "notebook-profile",
                "force_refresh": True,
            },
        )
        self.assertEqual(locked_response.status_code, 200)
        locked = locked_response.json()["data"]
        self.assertFalse(locked["is_unlocked"])
        self.assertEqual(locked["signals"]["conversation_count"], 0)

        now = datetime.now(UTC)
        quiz = ClassroomQuizArtifact(
            quiz_id="quiz-profile",
            user_id="profile-user",
            course_id="course-ds",
            notebook_id="notebook-profile",
            title="Profile quiz",
            questions=[
                {
                    "question_id": "q-active",
                    "type": "single_choice",
                    "stem": "Which traversal expands by layers?",
                    "options": ["BFS", "DFS", "Heap", "Stack"],
                    "answer": "BFS",
                    "explanation": "BFS expands graph nodes by layers.",
                }
            ],
        )
        flashcards = ClassroomFlashcardSet(
            flashcard_set_id="flashcards-profile",
            user_id="profile-user",
            course_id="course-ds",
            notebook_id="notebook-profile",
            title="Profile flashcards",
            cards=[{"card_id": "card-active", "front": "BFS uses?", "back": "Queue"}],
        )
        asyncio.run(self.repository.save_classroom_quiz(quiz))
        asyncio.run(self.repository.save_classroom_flashcard_set(flashcards))

        quiz_practice_response = self.client.post(
            "/api/classroom/quiz/practice",
            json={
                "user_id": "profile-user",
                "course_id": "course-ds",
                "quiz_id": "quiz-profile",
                "question_id": "q-active",
                "selected_answer": "BFS",
            },
        )
        self.assertEqual(quiz_practice_response.status_code, 200)
        self.assertTrue(quiz_practice_response.json()["data"]["is_correct"])

        flashcard_practice_response = self.client.post(
            "/api/classroom/flashcards/practice",
            json={
                "user_id": "profile-user",
                "course_id": "course-ds",
                "flashcard_set_id": "flashcards-profile",
                "attempt_id": "attempt-profile",
                "study_card_ids": ["card-active"],
                "card_id": "card-active",
                "result": "correct",
            },
        )
        self.assertEqual(flashcard_practice_response.status_code, 200)

        for index in range(14):
            session = TutorSession(
                session_id=f"profile-session-{index}",
                user_id="profile-user",
                course_id="course-ds",
                notebook_id="notebook-profile",
                question=f"Question {index}",
                updated_at=now + timedelta(seconds=index),
            )
            messages = [
                TutorMessage(
                    message_id=f"profile-message-user-{index}",
                    session_id=session.session_id,
                    role="user",
                    content=f"Question {index}",
                    created_at=now + timedelta(seconds=index),
                ),
                TutorMessage(
                    message_id=f"profile-message-ai-{index}",
                    session_id=session.session_id,
                    role="assistant",
                    content=f"Answer {index}",
                    created_at=now + timedelta(seconds=index, milliseconds=1),
                ),
            ]
            asyncio.run(self.repository.save_tutor_session(session))
            asyncio.run(self.repository.save_tutor_messages(messages))

        for index in range(35):
            asyncio.run(
                self.repository.save_quiz_practice_record(
                    QuizPracticeRecord(
                        record_id=f"quiz-window-{index}",
                        user_id="profile-user",
                        course_id="course-ds",
                        notebook_id="notebook-profile",
                        quiz_id=f"quiz-window-{index}",
                        question_id=f"q-window-{index}",
                        selected_answer="BFS",
                        correct_answer="BFS" if index % 2 == 0 else "DFS",
                        is_correct=index % 2 == 0,
                        updated_at=now + timedelta(seconds=index),
                    )
                )
            )
            asyncio.run(
                self.repository.save_flashcard_practice_record(
                    FlashcardPracticeRecord(
                        record_id=f"flashcard-window-{index}",
                        user_id="profile-user",
                        course_id="course-ds",
                        flashcard_set_id="flashcards-profile",
                        attempt_id=f"attempt-window-{index}",
                        study_card_ids=["card-active"],
                        card_id="card-active",
                        result="correct" if index % 2 == 0 else "incorrect",
                        attempt_completed=True,
                        updated_at=now + timedelta(seconds=index),
                    )
                )
            )

        profile_response = self.client.post(
            "/api/classroom/profile/generate",
            json={
                "user_id": "profile-user",
                "course_id": "course-ds",
                "notebook_id": "notebook-profile",
                "force_refresh": True,
            },
        )
        self.assertEqual(profile_response.status_code, 200)
        profile = profile_response.json()["data"]
        self.assertTrue(profile["is_unlocked"])
        self.assertEqual(profile["signals"]["conversation_count"], 12)
        self.assertEqual(profile["signals"]["quiz_attempt_count"], 30)
        self.assertEqual(profile["signals"]["flashcard_attempt_count"], 30)
        self.assertEqual(len(profile["radar"]), 6)
        self.assertEqual(profile["radar"][0]["key"], "conceptual_understanding")
        self.assertTrue(profile["recommendations"])
        self.assertTrue(profile["learning_resources"])
        self.assertEqual(profile["learning_resources"][0]["language"], "zh")

        recent_sessions = asyncio.run(
            self.repository.list_recent_tutor_sessions(
                user_id="profile-user",
                course_id="course-ds",
                notebook_id="notebook-profile",
                limit=50,
            )
        )
        recent_quiz_records = asyncio.run(
            self.repository.list_recent_quiz_practice_records(
                user_id="profile-user",
                course_id="course-ds",
                notebook_id="notebook-profile",
                limit=50,
            )
        )
        recent_flashcard_records = asyncio.run(
            self.repository.list_recent_flashcard_practice_records(
                user_id="profile-user",
                flashcard_set_ids={"flashcards-profile"},
                limit=50,
            )
        )
        self.assertEqual(len(recent_sessions), 12)
        self.assertEqual(len(recent_quiz_records), 30)
        self.assertEqual(len(recent_flashcard_records), 30)

    def test_user_profile_falls_back_when_ai_returns_invalid_payload(self):
        self.ai_client = InvalidUserProfileAIClient()
        now = datetime.now(UTC)
        session = TutorSession(
            session_id="profile-invalid-session",
            user_id="profile-invalid-user",
            course_id="course-ds",
            notebook_id="notebook-profile",
            question="How should I review BFS?",
            updated_at=now,
        )
        messages = [
            TutorMessage(
                message_id="profile-invalid-user-message",
                session_id=session.session_id,
                role="user",
                content="How should I review BFS?",
                created_at=now,
            ),
            TutorMessage(
                message_id="profile-invalid-ai-message",
                session_id=session.session_id,
                role="assistant",
                content="Review BFS with queue examples and one shortest path exercise.",
                created_at=now,
            ),
        ]
        asyncio.run(self.repository.save_tutor_session(session))
        asyncio.run(self.repository.save_tutor_messages(messages))

        response = self.client.post(
            "/api/classroom/profile/generate",
            json={
                "user_id": "profile-invalid-user",
                "course_id": "course-ds",
                "notebook_id": "notebook-profile",
                "force_refresh": True,
            },
        )

        self.assertEqual(response.status_code, 200)
        profile = response.json()["data"]
        self.assertTrue(profile["is_unlocked"])
        self.assertEqual(len(profile["radar"]), 6)
        self.assertTrue(profile["recommendations"])
        self.assertTrue(profile["learning_resources"])
        self.assertTrue(profile["learning_resources"][0]["url"].startswith("https://"))

    def test_user_profile_learning_resources_prefer_mooc_and_bilibili_pages(self):
        self.ai_client = MixedLearningResourceAIClient()
        now = datetime.now(UTC)
        session = TutorSession(
            session_id="profile-resource-session",
            user_id="profile-resource-user",
            course_id="course-ds",
            notebook_id="notebook-profile",
            question="How should I review data structures?",
            updated_at=now,
        )
        messages = [
            TutorMessage(
                message_id="profile-resource-user-message",
                session_id=session.session_id,
                role="user",
                content="How should I review data structures?",
                created_at=now,
            ),
            TutorMessage(
                message_id="profile-resource-ai-message",
                session_id=session.session_id,
                role="assistant",
                content="Use a MOOC course and a video lecture series.",
                created_at=now,
            ),
        ]
        asyncio.run(self.repository.save_tutor_session(session))
        asyncio.run(self.repository.save_tutor_messages(messages))

        response = self.client.post(
            "/api/classroom/profile/generate",
            json={
                "user_id": "profile-resource-user",
                "course_id": "course-ds",
                "notebook_id": "notebook-profile",
                "force_refresh": True,
            },
        )

        self.assertEqual(response.status_code, 200)
        resources = response.json()["data"]["learning_resources"]
        urls = [item["url"] for item in resources]
        self.assertIn("https://www.icourse163.org/course/ZJU-93001", urls)
        self.assertIn("https://www.bilibili.com/video/BV1b7411N798/", urls)
        self.assertNotIn("https://www.icourse163.org/", urls)
        self.assertNotIn("https://www.bilibili.com/video/BV0000000000/", urls)
        self.assertFalse(any("search.bilibili.com" in url for url in urls))
        self.assertFalse(any("example.com" in url for url in urls))
        self.assertTrue(
            all(
                "icourse163.org/course/" in url
                or "bilibili.com/video/BV" in url
                or "xuetangx.com/course/" in url
                or "higher.smartedu.cn/course" in url
                for url in urls
            )
        )

    def test_user_profile_get_sanitizes_legacy_cached_learning_resources(self):
        asyncio.run(
            self.repository.save_user_profile(
                {
                    "user_id": "profile-legacy-resource-user",
                    "course_id": "course-ds",
                    "notebook_id": "notebook-profile",
                    "is_unlocked": True,
                    "generated_at": datetime.now(UTC).isoformat(),
                    "window": {
                        "conversation_limit": 12,
                        "quiz_practice_limit": 30,
                        "flashcard_practice_limit": 30,
                    },
                    "signals": {
                        "conversation_count": 1,
                        "message_count": 2,
                        "quiz_attempt_count": 0,
                        "flashcard_attempt_count": 0,
                        "quiz_accuracy": 0.0,
                        "flashcard_accuracy": 0.0,
                    },
                    "summary": "Cached profile.",
                    "radar": [],
                    "learning_traits": [],
                    "strengths": [],
                    "risks": [],
                    "recommendations": [],
                    "learning_resources": [
                        {
                            "title": "Old wiki",
                            "url": "https://oi-wiki.org/",
                            "language": "zh",
                            "reason": "Legacy source should be filtered.",
                        },
                        {
                            "title": "Old OCW search",
                            "url": "https://ocw.mit.edu/search/",
                            "language": "en",
                            "reason": "Legacy source should be filtered.",
                        },
                    ],
                    "_generation": {"source": "ai", "reason": "success"},
                }
            )
        )

        response = self.client.get(
            "/api/classroom/profile",
            params={
                "user_id": "profile-legacy-resource-user",
                "course_id": "course-ds",
                "notebook_id": "notebook-profile",
            },
        )

        self.assertEqual(response.status_code, 200)
        profile = response.json()["data"]
        urls = [item["url"] for item in profile["learning_resources"]]
        self.assertNotIn("https://oi-wiki.org/", urls)
        self.assertNotIn("https://ocw.mit.edu/search/", urls)
        self.assertTrue(urls)
        self.assertTrue(
            all("icourse163.org/course/" in url or "bilibili.com/video/BV" in url for url in urls)
        )

    def test_user_profile_learning_resources_are_scoped_to_notebook_topic(self):
        self.repository._notebooks["network-notebook"] = {
            "user_id": "profile-network-resource-user",
            "course_id": "course-network",
            "notebook_id": "network-notebook",
            "knowledge_point_id": "network-notebook",
            "title": "计算机网络",
        }
        asyncio.run(
            self.repository.save_user_profile(
                {
                    "user_id": "profile-network-resource-user",
                    "course_id": "course-network",
                    "notebook_id": "network-notebook",
                    "is_unlocked": True,
                    "generated_at": datetime.now(UTC).isoformat(),
                    "window": {
                        "conversation_limit": 12,
                        "quiz_practice_limit": 30,
                        "flashcard_practice_limit": 30,
                    },
                    "signals": {
                        "conversation_count": 1,
                        "message_count": 2,
                        "quiz_attempt_count": 0,
                        "flashcard_attempt_count": 0,
                        "quiz_accuracy": 0.0,
                        "flashcard_accuracy": 0.0,
                    },
                    "summary": "Cached profile.",
                    "radar": [],
                    "learning_traits": [],
                    "strengths": [],
                    "risks": [],
                    "recommendations": [],
                    "learning_resources": [
                        {
                            "title": "数据结构课程",
                            "url": "https://www.icourse163.org/course/ZJU-93001",
                            "language": "zh",
                            "reason": "Off-topic verified course should be filtered.",
                        },
                        {
                            "title": "操作系统课程",
                            "url": "https://www.bilibili.com/video/BV1YE411D7nH/",
                            "language": "zh",
                            "reason": "Off-topic verified video should be filtered.",
                        },
                    ],
                    "_generation": {"source": "ai", "reason": "success"},
                }
            )
        )

        response = self.client.get(
            "/api/classroom/profile",
            params={
                "user_id": "profile-network-resource-user",
                "course_id": "course-network",
                "notebook_id": "network-notebook",
            },
        )

        self.assertEqual(response.status_code, 200)
        profile = response.json()["data"]
        self.assertNotIn("_generation", profile)
        urls = [item["url"] for item in profile["learning_resources"]]
        self.assertEqual(
            set(urls),
            {
                "https://www.icourse163.org/course/HIT-154005",
                "https://www.icourse163.org/course/USTC-1003381001",
                "https://www.bilibili.com/video/BV1H4kwYHEcR/",
                "https://www.bilibili.com/video/BV1PK4y1X7ze/",
                "https://www.bilibili.com/video/BV1Pt41137w6/",
                "https://www.bilibili.com/video/BV19E411D78Q/",
            },
        )
        self.assertFalse(any("ZJU-93001" in url for url in urls))
        self.assertFalse(any("BV1YE411D7nH" in url for url in urls))

    def test_user_profile_timeout_uses_fallback_payload(self):
        self.ai_client = SlowUserProfileAIClient()
        original_timeout = classroom_service_module.USER_PROFILE_AI_TIMEOUT_SECONDS
        classroom_service_module.USER_PROFILE_AI_TIMEOUT_SECONDS = 0.01
        now = datetime.now(UTC)
        session = TutorSession(
            session_id="profile-timeout-session",
            user_id="profile-timeout-user",
            course_id="course-ds",
            notebook_id="notebook-profile",
            question="How should I review network layers?",
            updated_at=now,
        )
        messages = [
            TutorMessage(
                message_id="profile-timeout-user-message",
                session_id=session.session_id,
                role="user",
                content="How should I review network layers?",
                created_at=now,
            ),
            TutorMessage(
                message_id="profile-timeout-ai-message",
                session_id=session.session_id,
                role="assistant",
                content="Review each layer with one protocol example.",
                created_at=now,
            ),
        ]
        asyncio.run(self.repository.save_tutor_session(session))
        asyncio.run(self.repository.save_tutor_messages(messages))

        try:
            with self.assertLogs(
                "app.services.classroom_service",
                level="WARNING",
            ) as logs:
                response = self.client.post(
                    "/api/classroom/profile/generate",
                    json={
                        "user_id": "profile-timeout-user",
                        "course_id": "course-ds",
                        "notebook_id": "notebook-profile",
                        "force_refresh": True,
                    },
                )
        finally:
            classroom_service_module.USER_PROFILE_AI_TIMEOUT_SECONDS = original_timeout

        self.assertEqual(response.status_code, 200)
        profile = response.json()["data"]
        self.assertNotIn("_generation", profile)
        self.assertTrue(profile["is_unlocked"])
        self.assertEqual(profile["signals"]["conversation_count"], 1)
        self.assertEqual(len(profile["radar"]), 6)
        self.assertTrue(profile["recommendations"])
        self.assertTrue(profile["learning_resources"])
        self.assertIn("returning rule fallback profile", "\n".join(logs.output))
        saved_profile = asyncio.run(
            self.repository.get_user_profile(
                user_id="profile-timeout-user",
                course_id="course-ds",
                notebook_id="notebook-profile",
            )
        )
        self.assertEqual(saved_profile["_generation"]["source"], "fallback")
        self.assertEqual(saved_profile["_generation"]["reason"], "timeout")

    def test_user_profile_timeout_returns_cached_profile_when_available(self):
        now = datetime.now(UTC)
        session = TutorSession(
            session_id="profile-timeout-cache-session",
            user_id="profile-timeout-cache-user",
            course_id="course-ds",
            notebook_id="notebook-profile",
            question="How do I review transport protocols?",
            updated_at=now,
        )
        messages = [
            TutorMessage(
                message_id="profile-timeout-cache-user-message",
                session_id=session.session_id,
                role="user",
                content="How do I review transport protocols?",
                created_at=now,
            ),
            TutorMessage(
                message_id="profile-timeout-cache-ai-message",
                session_id=session.session_id,
                role="assistant",
                content="Compare TCP and UDP with packet examples.",
                created_at=now,
            ),
        ]
        asyncio.run(self.repository.save_tutor_session(session))
        asyncio.run(self.repository.save_tutor_messages(messages))

        first_response = self.client.post(
            "/api/classroom/profile/generate",
            json={
                "user_id": "profile-timeout-cache-user",
                "course_id": "course-ds",
                "notebook_id": "notebook-profile",
                "force_refresh": True,
            },
        )
        self.assertEqual(first_response.status_code, 200)
        cached_at = first_response.json()["data"]["generated_at"]
        saved_profile = asyncio.run(
            self.repository.get_user_profile(
                user_id="profile-timeout-cache-user",
                course_id="course-ds",
                notebook_id="notebook-profile",
            )
        )
        self.assertEqual(saved_profile["_generation"]["source"], "ai")

        self.ai_client = SlowUserProfileAIClient()
        original_timeout = classroom_service_module.USER_PROFILE_AI_TIMEOUT_SECONDS
        classroom_service_module.USER_PROFILE_AI_TIMEOUT_SECONDS = 0.01
        try:
            with self.assertLogs(
                "app.services.classroom_service",
                level="WARNING",
            ) as logs:
                timeout_response = self.client.post(
                    "/api/classroom/profile/generate",
                    json={
                        "user_id": "profile-timeout-cache-user",
                        "course_id": "course-ds",
                        "notebook_id": "notebook-profile",
                        "force_refresh": True,
                    },
                )
        finally:
            classroom_service_module.USER_PROFILE_AI_TIMEOUT_SECONDS = original_timeout

        self.assertEqual(timeout_response.status_code, 200)
        profile = timeout_response.json()["data"]
        self.assertNotIn("_generation", profile)
        self.assertEqual(profile["generated_at"], cached_at)
        self.assertIn("returning cached profile", "\n".join(logs.output))
        stored_after_timeout = asyncio.run(
            self.repository.get_user_profile(
                user_id="profile-timeout-cache-user",
                course_id="course-ds",
                notebook_id="notebook-profile",
            )
        )
        self.assertEqual(stored_after_timeout["_generation"]["source"], "ai")

    def test_user_profile_get_reads_saved_profile_without_regenerating(self):
        self.ai_client = CountingUserProfileAIClient()
        now = datetime.now(UTC)
        session = TutorSession(
            session_id="profile-cache-session",
            user_id="profile-cache-user",
            course_id="course-ds",
            notebook_id="notebook-profile",
            question="How do I review queues?",
            updated_at=now,
        )
        asyncio.run(self.repository.save_tutor_session(session))
        asyncio.run(
            self.repository.save_tutor_messages(
                [
                    TutorMessage(
                        message_id="profile-cache-message-user",
                        session_id=session.session_id,
                        role="user",
                        content="How do I review queues?",
                        created_at=now,
                    ),
                    TutorMessage(
                        message_id="profile-cache-message-ai",
                        session_id=session.session_id,
                        role="assistant",
                        content="Use queue operation examples and a BFS trace.",
                        created_at=now,
                    ),
                ]
            )
        )

        generate_response = self.client.post(
            "/api/classroom/profile/generate",
            json={
                "user_id": "profile-cache-user",
                "course_id": "course-ds",
                "notebook_id": "notebook-profile",
                "force_refresh": True,
            },
        )
        self.assertEqual(generate_response.status_code, 200)
        self.assertEqual(self.ai_client.profile_call_count, 1)
        generated_at = generate_response.json()["data"]["generated_at"]

        read_response = self.client.get(
            "/api/classroom/profile",
            params={
                "user_id": "profile-cache-user",
                "course_id": "course-ds",
                "notebook_id": "notebook-profile",
            },
        )
        self.assertEqual(read_response.status_code, 200)
        self.assertEqual(self.ai_client.profile_call_count, 1)
        self.assertEqual(read_response.json()["data"]["generated_at"], generated_at)

        regenerate_response = self.client.post(
            "/api/classroom/profile/generate",
            json={
                "user_id": "profile-cache-user",
                "course_id": "course-ds",
                "notebook_id": "notebook-profile",
                "force_refresh": True,
            },
        )
        self.assertEqual(regenerate_response.status_code, 200)
        self.assertEqual(self.ai_client.profile_call_count, 2)

    def test_rag_file_upload_and_classroom_study_tools(self):
        upload_response = self.client.post(
            "/api/rag/upload-file",
            data={
                "user_id": "student-401",
                "course_id": "course-ds",
            },
            files={
                "file": (
                    "bfs-notes.md",
                    b"BFS uses a queue and expands graph nodes by layers.",
                    "text/markdown",
                )
            },
        )

        self.assertEqual(upload_response.status_code, 200)
        document_id = upload_response.json()["data"]["document_id"]

        foreign_upload_response = self.client.post(
            "/api/rag/upload-file",
            data={
                "user_id": "student-foreign",
                "course_id": "course-ds",
            },
            files={
                "file": (
                    "other-notes.md",
                    b"DFS uses a stack-like traversal pattern.",
                    "text/markdown",
                )
            },
        )
        self.assertEqual(foreign_upload_response.status_code, 200)
        foreign_document_id = foreign_upload_response.json()["data"]["document_id"]

        quiz_response = self.client.post(
            "/api/classroom/quiz/generate",
            json={
                "user_id": "student-401",
                "course_id": "course-ds",
                "source_document_ids": [document_id],
            },
        )
        self.assertEqual(quiz_response.status_code, 200)
        quiz = quiz_response.json()["data"]
        self.assertEqual(quiz["source_document_ids"], [document_id])
        self.assertEqual(quiz["questions"][0]["type"], "single_choice")
        self.assertEqual(len(quiz["questions"][0]["options"]), 4)
        self.assertEqual(
            set(quiz["questions"][0]["option_explanations"]),
            set(quiz["questions"][0]["options"]),
        )

        blocked_quiz_response = self.client.post(
            "/api/classroom/quiz/generate",
            json={
                "user_id": "student-401",
                "course_id": "course-ds",
                "source_document_ids": [foreign_document_id],
            },
        )
        self.assertEqual(blocked_quiz_response.status_code, 400)

        flashcards_response = self.client.post(
            "/api/classroom/flashcards/generate",
            json={
                "user_id": "student-401",
                "course_id": "course-ds",
                "source_document_ids": [document_id],
            },
        )
        self.assertEqual(flashcards_response.status_code, 200)
        flashcards = flashcards_response.json()["data"]
        self.assertEqual(flashcards["source_document_ids"], [document_id])
        self.assertEqual(flashcards["cards"][0]["back"], "A queue.")

        studio_response = self.client.get(
            "/api/classroom/studio",
            params={"user_id": "student-401", "course_id": "course-ds"},
        )
        self.assertEqual(studio_response.status_code, 200)
        studio = studio_response.json()["data"]
        self.assertEqual(studio["quizzes"][0]["quiz_id"], quiz["quiz_id"])
        self.assertEqual(
            studio["flashcard_sets"][0]["flashcard_set_id"],
            flashcards["flashcard_set_id"],
        )

        practice_response = self.client.post(
            "/api/classroom/flashcards/practice",
            json={
                "user_id": "student-401",
                "course_id": "course-ds",
                "flashcard_set_id": flashcards["flashcard_set_id"],
                "attempt_id": "attempt-1",
                "study_card_ids": [flashcards["cards"][0]["card_id"]],
                "card_id": flashcards["cards"][0]["card_id"],
                "result": "correct",
            },
        )
        self.assertEqual(practice_response.status_code, 200)
        practice = practice_response.json()["data"]
        self.assertEqual(practice["result"], "correct")
        self.assertEqual(practice["attempt_id"], "attempt-1")
        self.assertTrue(practice["attempt_completed"])

        studio_after_practice_response = self.client.get(
            "/api/classroom/studio",
            params={"user_id": "student-401", "course_id": "course-ds"},
        )
        practice_records = studio_after_practice_response.json()["data"][
            "flashcard_records"
        ]
        self.assertEqual(len(practice_records), 1)
        self.assertEqual(practice_records[0]["card_id"], flashcards["cards"][0]["card_id"])

        second_attempt_response = self.client.post(
            "/api/classroom/flashcards/practice",
            json={
                "user_id": "student-401",
                "course_id": "course-ds",
                "flashcard_set_id": flashcards["flashcard_set_id"],
                "attempt_id": "attempt-2",
                "study_card_ids": [flashcards["cards"][0]["card_id"]],
                "card_id": flashcards["cards"][0]["card_id"],
                "result": "incorrect",
            },
        )
        self.assertEqual(second_attempt_response.status_code, 200)

        studio_with_two_attempts = self.client.get(
            "/api/classroom/studio",
            params={"user_id": "student-401", "course_id": "course-ds"},
        ).json()["data"]["flashcard_records"]
        self.assertEqual(
            {record["attempt_id"] for record in studio_with_two_attempts},
            {"attempt-1", "attempt-2"},
        )

        reset_response = self.client.post(
            f"/api/classroom/flashcards/{flashcards['flashcard_set_id']}/practice/reset",
            json={"user_id": "student-401"},
        )
        self.assertEqual(reset_response.status_code, 200)

        studio_after_reset_response = self.client.get(
            "/api/classroom/studio",
            params={"user_id": "student-401", "course_id": "course-ds"},
        )
        self.assertEqual(
            studio_after_reset_response.json()["data"]["flashcard_records"],
            [],
        )

        practice_again_response = self.client.post(
            "/api/classroom/flashcards/practice",
            json={
                "user_id": "student-401",
                "course_id": "course-ds",
                "flashcard_set_id": flashcards["flashcard_set_id"],
                "attempt_id": "attempt-3",
                "study_card_ids": [flashcards["cards"][0]["card_id"]],
                "card_id": flashcards["cards"][0]["card_id"],
                "result": "incorrect",
            },
        )
        self.assertEqual(practice_again_response.status_code, 200)

        delete_flashcards_response = self.client.delete(
            f"/api/classroom/flashcards/{flashcards['flashcard_set_id']}",
            params={"user_id": "student-401"},
        )
        self.assertEqual(delete_flashcards_response.status_code, 200)
        self.assertTrue(delete_flashcards_response.json()["data"]["deleted"])

        delete_quiz_response = self.client.delete(
            f"/api/classroom/quiz/{quiz['quiz_id']}",
            params={"user_id": "student-401"},
        )
        self.assertEqual(delete_quiz_response.status_code, 200)
        self.assertTrue(delete_quiz_response.json()["data"]["deleted"])

        studio_after_delete_response = self.client.get(
            "/api/classroom/studio",
            params={"user_id": "student-401", "course_id": "course-ds"},
        )
        studio_after_delete = studio_after_delete_response.json()["data"]
        self.assertEqual(studio_after_delete["quizzes"], [])
        self.assertEqual(studio_after_delete["flashcard_sets"], [])
        self.assertEqual(studio_after_delete["flashcard_records"], [])


if __name__ == "__main__":
    unittest.main()
