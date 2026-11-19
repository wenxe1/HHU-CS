import asyncio
import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient

from app.api.dependencies import get_notebook_service
from app.main import app
from app.services.notebook_service import (
    InMemoryNotebookRepository,
    NotebookService,
)


class NotebookApiTest(unittest.TestCase):
    def setUp(self):
        self.repository = InMemoryNotebookRepository()
        app.dependency_overrides[get_notebook_service] = lambda: NotebookService(
            self.repository,
        )
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_create_trims_title_and_persists_user_owned_notebook(self):
        response = self.client.post(
            "/api/notebooks",
            json={"user_id": "student-1", "title": "  数据结构  "},
        )

        self.assertEqual(response.status_code, 200)
        notebook = response.json()["data"]
        self.assertEqual(notebook["title"], "数据结构")
        self.assertEqual(notebook["user_id"], "student-1")
        self.assertEqual(notebook["course_id"], notebook["notebook_id"])
        self.assertEqual(notebook["knowledge_point_id"], notebook["notebook_id"])
        self.assertEqual(notebook["source_count"], 0)

        stored = asyncio.run(
            self.repository.get_notebook(notebook["notebook_id"], "student-1")
        )
        self.assertIsNotNone(stored)

    def test_list_and_detail_are_scoped_to_user(self):
        first = self.client.post(
            "/api/notebooks",
            json={"user_id": "student-1", "title": "我的笔记本"},
        ).json()["data"]
        self.client.post(
            "/api/notebooks",
            json={"user_id": "student-2", "title": "其他用户的笔记本"},
        )

        list_response = self.client.get(
            "/api/notebooks",
            params={"user_id": "student-1"},
        )
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(
            [item["notebook_id"] for item in list_response.json()["data"]],
            [first["notebook_id"]],
        )

        own_detail = self.client.get(
            f"/api/notebooks/{first['notebook_id']}",
            params={"user_id": "student-1"},
        )
        foreign_detail = self.client.get(
            f"/api/notebooks/{first['notebook_id']}",
            params={"user_id": "student-2"},
        )
        self.assertEqual(own_detail.status_code, 200)
        self.assertEqual(foreign_detail.status_code, 404)

    def test_create_rejects_whitespace_only_title(self):
        response = self.client.post(
            "/api/notebooks",
            json={"user_id": "student-1", "title": "   "},
        )
        self.assertEqual(response.status_code, 400)

    def test_update_title_persists_to_notebook(self):
        notebook = self.client.post(
            "/api/notebooks",
            json={"user_id": "student-1", "title": "旧标题"},
        ).json()["data"]

        response = self.client.patch(
            f"/api/notebooks/{notebook['notebook_id']}",
            params={"user_id": "student-1"},
            json={"title": "  新标题  "},
        )

        self.assertEqual(response.status_code, 200)
        updated = response.json()["data"]
        self.assertEqual(updated["title"], "新标题")

        stored = asyncio.run(
            self.repository.get_notebook(notebook["notebook_id"], "student-1")
        )
        self.assertIsNotNone(stored)
        self.assertEqual(stored.title, "新标题")

    def test_delete_removes_user_owned_notebook(self):
        notebook = self.client.post(
            "/api/notebooks",
            json={"user_id": "student-1", "title": "待删除"},
        ).json()["data"]

        response = self.client.delete(
            f"/api/notebooks/{notebook['notebook_id']}",
            params={"user_id": "student-1"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["data"]["deleted"])

        stored = asyncio.run(
            self.repository.get_notebook(notebook["notebook_id"], "student-1")
        )
        self.assertIsNone(stored)

        detail = self.client.get(
            f"/api/notebooks/{notebook['notebook_id']}",
            params={"user_id": "student-1"},
        )
        self.assertEqual(detail.status_code, 404)


if __name__ == "__main__":
    unittest.main()
