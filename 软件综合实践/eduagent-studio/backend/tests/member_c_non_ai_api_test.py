import sys
import unittest
from pathlib import Path
from uuid import uuid4

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient

from app.main import app


class MemberCNonAISmokeTest(unittest.TestCase):
    def setUp(self):
        self.suffix = uuid4().hex[:8]

    def test_non_ai_routes_and_error_contracts(self):
        with TestClient(app) as client:
            self._run_non_ai_routes_and_error_contracts(client)

    def _run_non_ai_routes_and_error_contracts(self, client: TestClient):
        health = client.get("/")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["message"], "EduAgent Studio backend is running")

        rag_list = client.get(
            "/api/rag/documents",
            params={"course_id": f"manual-missing-course-{self.suffix}"},
        )
        self.assertEqual(rag_list.status_code, 200)
        self.assertEqual(rag_list.json()["code"], 0)
        self.assertEqual(rag_list.json()["data"]["items"], [])
        self.assertEqual(rag_list.json()["data"]["total"], 0)

        resource_list = client.get(
            "/api/resource/list",
            params={"course_id": f"manual-missing-course-{self.suffix}"},
        )
        self.assertEqual(resource_list.status_code, 200)
        self.assertEqual(resource_list.json()["code"], 0)
        self.assertEqual(resource_list.json()["data"]["items"], [])
        self.assertEqual(resource_list.json()["data"]["total"], 0)

        missing_resource = client.get("/api/resource/not-exist")
        self.assertEqual(missing_resource.status_code, 404)
        self.assertEqual(missing_resource.json()["code"], 404)
        self.assertEqual(missing_resource.json()["message"], "resource not found")

        missing_task = client.get("/api/task/not-exist")
        self.assertEqual(missing_task.status_code, 404)
        self.assertEqual(missing_task.json()["code"], 404)
        self.assertEqual(missing_task.json()["message"], "task not found")

        missing_classroom = client.get("/api/classroom/not-exist")
        self.assertEqual(missing_classroom.status_code, 404)
        self.assertEqual(missing_classroom.json()["code"], 404)
        self.assertEqual(missing_classroom.json()["message"], "classroom not found")

        invalid_generate = client.post(
            "/api/resource/generate",
            json={"user_id": f"manual-student-{self.suffix}"},
        )
        self.assertEqual(invalid_generate.status_code, 422)


if __name__ == "__main__":
    unittest.main()
