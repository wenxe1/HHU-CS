import sys
import unittest
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

from bson import ObjectId
from fastapi.testclient import TestClient
from pymongo import MongoClient
from pymongo.errors import PyMongoError, ServerSelectionTimeoutError

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.config import DATABASE_NAME, MONGODB_URL
from app.main import app


def _database_name() -> str:
    return urlparse(MONGODB_URL).path.strip("/") or DATABASE_NAME


def _mongo_client() -> MongoClient:
    return MongoClient(MONGODB_URL, serverSelectionTimeoutMS=1000)


class BackendMainFlowIntegrationTest(unittest.TestCase):
    def setUp(self):
        try:
            self.mongo = _mongo_client()
            self.mongo.admin.command("ping")
        except (PyMongoError, ServerSelectionTimeoutError) as exc:
            raise unittest.SkipTest(f"MongoDB is required for live integration: {exc}")

        self.db = self.mongo[_database_name()]
        self.prefix = f"live-main-flow-{uuid4().hex[:8]}"
        self.user_id = str(ObjectId())
        self.teacher_id = str(ObjectId())
        self.course_id: str | None = None
        self.knowledge_point_ids: list[str] = []
        self.resource_ids: list[str] = []
        self.task_id: str | None = None
        self.document_id: str | None = None
        self.classroom_session_id: str | None = None

        self.client_context = TestClient(app)
        self.client = self.client_context.__enter__()

    def tearDown(self):
        if hasattr(self, "client_context"):
            self.client_context.__exit__(None, None, None)

        if not hasattr(self, "db"):
            return

        user_oid = ObjectId(self.user_id)
        if self.knowledge_point_ids:
            kp_oids = [ObjectId(item) for item in self.knowledge_point_ids]
            self.db.questions.delete_many({"knowledge_point_id": {"$in": kp_oids}})
            self.db.knowledge_points.delete_many({"_id": {"$in": kp_oids}})
        if self.course_id:
            self.db.courses.delete_many({"_id": ObjectId(self.course_id)})

        self.db.answer_records.delete_many({"user_id": user_oid})

        self.db.agent_task.delete_many({"user_id": self.user_id})
        self.db.learning_resource.delete_many({"user_id": self.user_id})
        self.db.tutor_session.delete_many({"user_id": self.user_id})
        self.db.tutor_message.delete_many({"user_id": self.user_id})
        self.db.code_review_record.delete_many({"user_id": self.user_id})
        self.db.rag_document.delete_many({"course_id": self.course_id})
        self.db.rag_chunk.delete_many({"course_id": self.course_id})
        if self.resource_ids:
            self.db.content_audit.delete_many(
                {"resource_id": {"$in": self.resource_ids}}
            )
        self.db.classroom_session.delete_many({"user_id": self.user_id})
        if self.classroom_session_id:
            self.db.classroom_scene.delete_many(
                {"session_id": self.classroom_session_id}
            )

        self.mongo.close()

    def test_live_ai_resource_and_agent_flow(self):
        course = self._post_json(
            "/api/courses",
            {
                "name": self.prefix,
                "description": "live backend main flow integration course",
            },
        )
        self.course_id = course["id"]

        current_kp_id = self._create_knowledge_point("array", 1)
        self._create_knowledge_point(
            "linked-list",
            2,
            prerequisites=[current_kp_id],
        )

        rag_upload = self._post_json(
            "/api/rag/upload",
            {
                "user_id": self.teacher_id,
                "course_id": self.course_id,
                "filename": f"{self.prefix}-array-notes.md",
                "content": (
                    "Array is a linear data structure with contiguous memory. "
                    "Indexed random access has O(1) time complexity. "
                    "Linked list nodes store values and references, so traversal is O(n)."
                ),
                "content_type": "text/markdown",
                "source_type": "course_material",
                "metadata": {"scenario": "live-main-flow"},
            },
        )
        self.document_id = rag_upload["document_id"]
        self.assertGreaterEqual(rag_upload["chunk_count"], 1)

        generated = self._post_json(
            "/api/resource/generate",
            {
                "user_id": self.user_id,
                "course_id": self.course_id,
                "knowledge_point_id": current_kp_id,
                "resource_types": ["lecture", "exercise"],
            },
        )
        self.task_id = generated["task_id"]
        self.resource_ids = generated["resource_ids"]
        self.assertEqual(generated["status"], "completed")
        self.assertEqual(len(self.resource_ids), 2)

        task = self._get_json(f"/api/task/{self.task_id}")
        self.assertEqual(task["status"], "completed")
        self.assertEqual(task["progress"], 100)

        resources = self._get_json(
            "/api/resource/list",
            params={
                "user_id": self.user_id,
                "course_id": self.course_id,
                "knowledge_point_id": current_kp_id,
            },
        )
        self.assertEqual(resources["total"], 2)
        self.assertEqual(
            {item["knowledge_point_id"] for item in resources["items"]},
            {current_kp_id},
        )

        first_resource = self._get_json(f"/api/resource/{self.resource_ids[0]}")
        self.assertEqual(first_resource["user_id"], self.user_id)
        self.assertEqual(first_resource["course_id"], self.course_id)
        self.assertEqual(first_resource["knowledge_point_id"], current_kp_id)
        self.assertTrue(first_resource["content"].get("rag_context"))

        audit = self._post_json(
            f"/api/audit/resource/{self.resource_ids[0]}",
            {
                "auditor_id": self.teacher_id,
                "strictness": "standard",
            },
        )
        self.assertIn(audit["status"], ["approved", "rejected"])
        self.assertIn(audit["risk_level"], ["low", "medium", "high"])

        classroom = self._post_json(
            "/api/classroom/generate",
            {
                "user_id": self.user_id,
                "course_id": self.course_id,
                "knowledge_point_id": current_kp_id,
                "topic": "array random access",
                "source_document_ids": [self.document_id],
            },
        )
        self.classroom_session_id = classroom["session_id"]
        self.assertEqual(classroom["status"], "completed")
        self.assertGreaterEqual(classroom["scene_count"], 3)

        classroom_detail = self._get_json(
            f"/api/classroom/{self.classroom_session_id}"
        )
        self.assertEqual(classroom_detail["user_id"], self.user_id)
        self.assertEqual(classroom_detail["course_id"], self.course_id)
        self.assertEqual(classroom_detail["knowledge_point_id"], current_kp_id)

        tutor = self._post_json(
            "/api/classroom/ask",
            {
                "user_id": self.user_id,
                "course_id": self.course_id,
                "knowledge_point_id": current_kp_id,
                "question": "How should I review this knowledge point?",
            },
        )
        self.assertTrue(tutor["answer"])
        self.assertGreaterEqual(len(tutor["guidance_steps"]), 1)

    def _create_knowledge_point(
        self,
        name: str,
        order: int,
        prerequisites: list[str] | None = None,
    ) -> str:
        data = self._post_json(
            "/api/knowledge-points",
            {
                "course_id": self.course_id,
                "chapter": "integration",
                "name": f"{self.prefix}-{name}",
                "description": "live backend main flow integration knowledge point",
                "difficulty": "basic",
                "prerequisites": prerequisites or [],
                "order": order,
            },
        )
        self.knowledge_point_ids.append(data["id"])
        return data["id"]

    def _post_json(self, url: str, payload: dict) -> dict:
        response = self.client.post(url, json=payload)
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["code"], 0, body)
        return body["data"]

    def _put_json(self, url: str, payload: dict) -> dict:
        response = self.client.put(url, json=payload)
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["code"], 0, body)
        return body["data"]

    def _get_json(self, url: str, params: dict | None = None) -> dict:
        response = self.client.get(url, params=params)
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["code"], 0, body)
        return body["data"]


if __name__ == "__main__":
    unittest.main()
