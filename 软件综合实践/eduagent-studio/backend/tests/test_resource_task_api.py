import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient

from app.api.dependencies import get_resource_generate_service, get_task_service
from app.db.repositories import InMemoryResourceTaskRepository
from app.main import app
from app.services.resource_service import ResourceGenerateService
from app.services.task_service import TaskService
from fakes import FakeAIClient


class ResourceTaskApiTest(unittest.TestCase):
    def setUp(self):
        self.repository = InMemoryResourceTaskRepository()
        self.ai_client = FakeAIClient()
        app.dependency_overrides[get_resource_generate_service] = (
            lambda: ResourceGenerateService(self.repository, self.ai_client)
        )
        app.dependency_overrides[get_task_service] = lambda: TaskService(
            self.repository
        )
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_generate_resource_creates_queryable_task_and_resources(self):
        response = self.client.post(
            "/api/resource/generate",
            json={
                "user_id": "student-001",
                "course_id": "course-ds",
                "knowledge_point_id": "kp-bfs",
                "resource_types": ["lecture", "exercise"],
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        task_id = body["data"]["task_id"]
        resource_ids = body["data"]["resource_ids"]
        self.assertEqual(len(resource_ids), 2)

        task_response = self.client.get(f"/api/task/{task_id}")
        self.assertEqual(task_response.status_code, 200)
        task = task_response.json()["data"]
        self.assertEqual(task["status"], "completed")
        self.assertEqual(task["progress"], 100)
        self.assertIn("资源生成中", [event["message"] for event in task["events"]])

        events_response = self.client.get(f"/api/task/{task_id}/events")
        self.assertEqual(events_response.status_code, 200)
        events_data = events_response.json()["data"]
        self.assertEqual(events_data["task_id"], task_id)
        self.assertEqual(events_data["events"][-1]["message"], "已完成")

        list_response = self.client.get(
            "/api/resource/list",
            params={
                "user_id": "student-001",
                "course_id": "course-ds",
                "knowledge_point_id": "kp-bfs",
                "type": "lecture",
            },
        )
        self.assertEqual(list_response.status_code, 200)
        items = list_response.json()["data"]["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["type"], "lecture")
        self.assertEqual(items[0]["task_id"], task_id)

        detail_response = self.client.get(f"/api/resource/{items[0]['resource_id']}")
        self.assertEqual(detail_response.status_code, 200)
        detail = detail_response.json()["data"]
        self.assertEqual(detail["resource_id"], items[0]["resource_id"])
        self.assertEqual(detail["audit_status"], "pending")

    def test_generate_all_d3_d4_resource_types_returns_structured_content(self):
        resource_types = ["lecture", "exercise", "mindmap", "slide", "code_lab"]

        response = self.client.post(
            "/api/resource/generate",
            json={
                "user_id": "student-d3d4",
                "course_id": "course-ds",
                "knowledge_point_id": "kp-graph-search",
                "resource_types": resource_types,
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["status"], "completed")
        self.assertEqual(len(data["resource_ids"]), 5)

        list_response = self.client.get(
            "/api/resource/list",
            params={"user_id": "student-d3d4", "course_id": "course-ds"},
        )
        self.assertEqual(list_response.status_code, 200)
        items = list_response.json()["data"]["items"]
        self.assertEqual({item["type"] for item in items}, set(resource_types))

        required_content_keys = {
            "lecture": "sections",
            "exercise": "question_bank",
            "mindmap": "root",
            "slide": "slides",
            "code_lab": "starter_code",
        }
        expected_agents = {
            "lecture": "Document Agent",
            "exercise": "Exercise Agent",
            "mindmap": "Mindmap Agent",
            "slide": "Slide Agent",
            "code_lab": "Code Lab Agent",
        }

        for item in items:
            detail_response = self.client.get(f"/api/resource/{item['resource_id']}")
            self.assertEqual(detail_response.status_code, 200)
            detail = detail_response.json()["data"]
            content = detail["content"]

            self.assertEqual(content["status"], "generated")
            self.assertEqual(content["agent"], expected_agents[item["type"]])
            self.assertIn(required_content_keys[item["type"]], content)
            self.assertEqual(
                content["personalization"]["knowledge_point_id"],
                "kp-graph-search",
            )

    def test_delete_resource_removes_it_from_detail_queries(self):
        generate_response = self.client.post(
            "/api/resource/generate",
            json={
                "user_id": "student-002",
                "course_id": "course-ai",
                "knowledge_point_id": "kp-search",
                "resource_types": ["mindmap"],
            },
        )
        self.assertEqual(generate_response.status_code, 200)
        resource_id = generate_response.json()["data"]["resource_ids"][0]

        delete_response = self.client.delete(f"/api/resource/{resource_id}")
        self.assertEqual(delete_response.status_code, 200)
        self.assertEqual(delete_response.json()["code"], 0)

        missing_response = self.client.get(f"/api/resource/{resource_id}")
        self.assertEqual(missing_response.status_code, 404)
        self.assertEqual(missing_response.json()["code"], 404)


if __name__ == "__main__":
    unittest.main()
