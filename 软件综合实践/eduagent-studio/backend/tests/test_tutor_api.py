import asyncio
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient

from app.api.dependencies import get_deepseek_tutor_service, get_tutor_service
from app.db.repositories import InMemoryResourceTaskRepository
from app.main import app
from app.schemas.rag import RAGUploadRequest
from app.services.rag_service import RAGService
from app.services.tutor_service import TutorService
from fakes import FakeAIClient


class PromptCaptureAIClient(FakeAIClient):
    def __init__(self):
        self.stream_text_calls = []

    async def stream_text(
        self,
        agent_name,
        system_prompt,
        user_prompt,
        use_reasoning=False,
    ):
        self.stream_text_calls.append(
            {
                "agent_name": agent_name,
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "use_reasoning": use_reasoning,
            }
        )
        async for chunk in super().stream_text(
            agent_name,
            system_prompt,
            user_prompt,
            use_reasoning,
        ):
            yield chunk


class SlowStreamingAIClient(FakeAIClient):
    async def stream_text(
        self,
        agent_name,
        system_prompt,
        user_prompt,
        use_reasoning=False,
    ):
        for chunk in ("持续", "输出", "较长", "回答"):
            await asyncio.sleep(0.02)
            yield chunk


class ClassroomChatApiTest(unittest.TestCase):
    def setUp(self):
        self.repository = InMemoryResourceTaskRepository()
        self.ai_client = FakeAIClient()
        app.dependency_overrides[get_tutor_service] = lambda: TutorService(
            self.repository,
            self.ai_client,
        )
        app.dependency_overrides[get_deepseek_tutor_service] = lambda: TutorService(
            self.repository,
            self.ai_client,
        )
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_classroom_ask_returns_answer_and_persists_session(self):
        response = self.client.post(
            "/api/classroom/ask",
            json={
                "user_id": "student-101",
                "course_id": "course-ds",
                "knowledge_point_id": "kp-bfs",
                "question": "BFS 为什么要用队列？",
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        data = body["data"]
        self.assertEqual(data["personalization"]["agent"], "Tutor Agent")
        self.assertEqual(data["personalization"]["knowledge_point_id"], "kp-bfs")
        self.assertGreaterEqual(len(data["guidance_steps"]), 3)

        session = asyncio.run(
            self.repository.get_tutor_session(data["session_id"])
        )
        messages = asyncio.run(
            self.repository.list_tutor_messages(data["session_id"])
        )
        self.assertIsNotNone(session)
        self.assertEqual(session.user_id, "student-101")
        self.assertEqual([message.role for message in messages], ["user", "assistant"])

        delete_response = self.client.delete(
            "/api/classroom/history",
            params={"user_id": "student-101", "course_id": "course-ds"},
        )
        self.assertEqual(delete_response.status_code, 200)
        delete_data = delete_response.json()["data"]
        self.assertTrue(delete_data["deleted"])
        self.assertEqual(delete_data["deleted_sessions"], 1)

        deleted_session = asyncio.run(
            self.repository.get_tutor_session(data["session_id"])
        )
        deleted_messages = asyncio.run(
            self.repository.list_tutor_messages(data["session_id"])
        )
        self.assertIsNone(deleted_session)
        self.assertEqual(deleted_messages, [])

    def test_classroom_ask_stream_returns_incremental_answer(self):
        response = self.client.post(
            "/api/classroom/ask/stream",
            json={
                "user_id": "student-101",
                "course_id": "course-ds",
                "knowledge_point_id": "kp-bfs",
                "question": "BFS 为什么要用队列？",
            },
        )

        self.assertEqual(response.status_code, 200)
        events = [json.loads(line) for line in response.text.splitlines() if line]
        self.assertEqual(
            [event["delta"] for event in events if event["type"] == "delta"],
            ["AI tutor ", "answer."],
        )
        completed = next(event["data"] for event in events if event["type"] == "done")
        self.assertEqual(completed["answer"], "AI tutor answer.")

    def test_classroom_stream_timeout_is_idle_not_total_duration(self):
        self.ai_client = SlowStreamingAIClient()
        with patch(
            "app.services.tutor_service.TUTOR_STREAM_IDLE_TIMEOUT_SECONDS",
            0.05,
        ):
            response = self.client.post(
                "/api/classroom/ask/stream",
                json={
                    "user_id": "student-101",
                    "course_id": "course-ds",
                    "question": "请给出一个较长的解释。",
                },
            )

        self.assertEqual(response.status_code, 200)
        events = [json.loads(line) for line in response.text.splitlines() if line]
        self.assertEqual(
            "".join(event["delta"] for event in events if event["type"] == "delta"),
            "持续输出较长回答",
        )
        completed = next(event["data"] for event in events if event["type"] == "done")
        self.assertEqual(completed["answer"], "持续输出较长回答")

    def test_history_can_be_deleted_for_one_notebook_visit_only(self):
        session_ids = []
        for visit_id in ("visit-a", "visit-b"):
            response = self.client.post(
                "/api/classroom/ask",
                json={
                    "user_id": "student-101",
                    "course_id": "course-ds",
                    "notebook_id": "notebook-a",
                    "visit_id": visit_id,
                    "question": "请解释队列。",
                },
            )
            self.assertEqual(response.status_code, 200)
            session_ids.append(response.json()["data"]["session_id"])

        delete_response = self.client.delete(
            "/api/classroom/history",
            params={"user_id": "student-101", "visit_id": "visit-a"},
        )

        self.assertEqual(delete_response.status_code, 200)
        self.assertEqual(delete_response.json()["data"]["deleted_sessions"], 1)
        self.assertIsNone(asyncio.run(self.repository.get_tutor_session(session_ids[0])))
        self.assertIsNotNone(asyncio.run(self.repository.get_tutor_session(session_ids[1])))

    def test_tutor_ask_uses_its_independent_service_dependency(self):
        response = self.client.post(
            "/api/tutor/ask",
            json={
                "user_id": "student-101",
                "question": "请解释队列的基本概念。",
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["answer"], "AI tutor answer.")
        self.assertEqual(data["guidance_steps"], [])
        self.assertEqual(data["follow_up_questions"], [])
        self.assertEqual(data["citations"], [])
        self.assertEqual(data["personalization"]["reasoning_basis"], ["plain_chat"])

    def test_tutor_ask_without_course_id_is_plain_chat(self):
        self.ai_client = PromptCaptureAIClient()
        response = self.client.post(
            "/api/tutor/ask",
            json={
                "user_id": "student-101",
                "course_name": "数据结构",
                "knowledge_point_id": "kp-bfs",
                "knowledge_point_name": "广度优先搜索",
                "question": "讲解这个知识点",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["answer"], "AI tutor answer.")
        self.assertEqual(len(self.ai_client.stream_text_calls), 1)
        call = self.ai_client.stream_text_calls[0]
        self.assertIn("纯 Chat 对话", call["system_prompt"])
        self.assertIn("当前课程：数据结构", call["system_prompt"])
        self.assertIn("当前选中的知识点：广度优先搜索", call["system_prompt"])
        self.assertIn("不要再询问具体课程或知识点是什么", call["system_prompt"])
        self.assertIn("不超过 3 个要点", call["system_prompt"])
        self.assertIn("300 个中文字符以内", call["system_prompt"])
        self.assertIn("不写客套开场或重复总结", call["system_prompt"])
        self.assertEqual(call["user_prompt"], "用户问题：讲解这个知识点")

    def test_classroom_ask_limits_retrieval_to_notebook_and_selected_sources(self):
        rag_service = RAGService(self.repository, self.ai_client)
        bfs_document = asyncio.run(
            rag_service.upload(
                RAGUploadRequest(
                    user_id="student-101",
                    course_id="course-ds",
                    notebook_id="notebook-a",
                    filename="bfs.md",
                    content="BFS uses a queue and expands nodes by layers.",
                )
            )
        )
        dfs_document = asyncio.run(
            rag_service.upload(
                RAGUploadRequest(
                    user_id="student-101",
                    course_id="course-ds",
                    notebook_id="notebook-a",
                    filename="dfs.md",
                    content="DFS explores one branch deeply before backtracking.",
                )
            )
        )
        other_notebook_document = asyncio.run(
            rag_service.upload(
                RAGUploadRequest(
                    user_id="student-101",
                    course_id="course-ds",
                    notebook_id="notebook-b",
                    filename="heap.md",
                    content="A heap supports efficient priority queue operations.",
                )
            )
        )

        selected_response = self.client.post(
            "/api/classroom/ask",
            json={
                "user_id": "student-101",
                "course_id": "course-ds",
                "notebook_id": "notebook-a",
                "question": "请总结这些资料。",
                "source_document_ids": [bfs_document["document_id"]],
            },
        )
        self.assertEqual(selected_response.status_code, 200)
        selected_citations = selected_response.json()["data"]["citations"]
        self.assertEqual(
            {citation["document_id"] for citation in selected_citations},
            {bfs_document["document_id"]},
        )

        default_response = self.client.post(
            "/api/classroom/ask",
            json={
                "user_id": "student-101",
                "course_id": "course-ds",
                "notebook_id": "notebook-a",
                "question": "请总结这些资料。",
            },
        )
        self.assertEqual(default_response.status_code, 200)
        default_document_ids = {
            citation["document_id"]
            for citation in default_response.json()["data"]["citations"]
        }
        self.assertIn(bfs_document["document_id"], default_document_ids)
        self.assertIn(dfs_document["document_id"], default_document_ids)
        self.assertNotIn(other_notebook_document["document_id"], default_document_ids)

        blocked_response = self.client.post(
            "/api/classroom/ask",
            json={
                "user_id": "student-101",
                "course_id": "course-ds",
                "notebook_id": "notebook-a",
                "question": "请总结这些资料。",
                "source_document_ids": [other_notebook_document["document_id"]],
            },
        )
        self.assertEqual(blocked_response.status_code, 200)
        blocked_data = blocked_response.json()["data"]
        self.assertEqual(blocked_data["citations"], [])
        self.assertIn("来源范围", blocked_data["answer"])


if __name__ == "__main__":
    unittest.main()
