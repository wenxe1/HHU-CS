import json
import sys
import time
import unittest
from pathlib import Path
from uuid import uuid4

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient

from app.main import app


class MemberCLiveApiTest(unittest.TestCase):
    def setUp(self):
        suffix = uuid4().hex[:8]
        self.user_id = f"manual-student-{suffix}"
        self.teacher_id = f"manual-teacher-{suffix}"
        self.course_id = f"manual-course-ds-{suffix}"
        self.knowledge_point_id = "kp-bfs"
        self.results: list[dict] = []

    def test_member_c_manual_flow(self):
        with TestClient(app) as client:
            self.client = client
            self._run_member_c_manual_flow()

    def _run_member_c_manual_flow(self):
        resource_ids: list[str] = []
        task_id = None
        classroom_session_id = None

        self._check("health", "GET", "/", expected_status=200)

        rag_body = {
            "user_id": self.teacher_id,
            "course_id": self.course_id,
            "filename": "graph-search.md",
            "content": (
                "BFS uses a queue to expand graph nodes level by level. "
                "It is suitable for shortest paths in unweighted graphs. "
                "A visited set prevents repeated visits and cycles."
            ),
            "content_type": "text/markdown",
            "source_type": "course_material",
            "metadata": {"chapter": "graph"},
        }
        rag_data = self._check(
            "rag upload",
            "POST",
            "/api/rag/upload",
            json_body=rag_body,
            required_data_keys=["document_id", "chunk_count", "chunks"],
        )
        if rag_data:
            self.assertGreaterEqual(rag_data["chunk_count"], 1)

        rag_list = self._check(
            "rag documents",
            "GET",
            "/api/rag/documents",
            params={"course_id": self.course_id},
            required_data_keys=["items", "total"],
        )
        if rag_list:
            self.assertGreaterEqual(rag_list["total"], 1)

        generate_data = self._check(
            "resource generate",
            "POST",
            "/api/resource/generate",
            json_body={
                "user_id": self.user_id,
                "course_id": self.course_id,
                "knowledge_point_id": self.knowledge_point_id,
                "resource_types": [
                    "lecture",
                    "exercise",
                    "mindmap",
                    "slide",
                    "code_lab",
                ],
            },
            required_data_keys=["task_id", "status", "resource_ids"],
            timeout_hint="This step calls the chat model several times.",
        )
        if generate_data:
            task_id = generate_data["task_id"]
            resource_ids = generate_data["resource_ids"]
            self.assertEqual(generate_data["status"], "completed")
            self.assertEqual(len(resource_ids), 5)

        if task_id:
            task_data = self._check(
                "task detail",
                "GET",
                f"/api/task/{task_id}",
                required_data_keys=["task_id", "status", "progress", "events"],
            )
            if task_data:
                self.assertEqual(task_data["status"], "completed")
                self.assertEqual(task_data["progress"], 100)

            events_data = self._check(
                "task events",
                "GET",
                f"/api/task/{task_id}/events",
                required_data_keys=["task_id", "events"],
            )
            if events_data:
                self.assertGreaterEqual(len(events_data["events"]), 1)

        list_data = self._check(
            "resource list",
            "GET",
            "/api/resource/list",
            params={
                "user_id": self.user_id,
                "course_id": self.course_id,
                "knowledge_point_id": self.knowledge_point_id,
            },
            required_data_keys=["items", "total"],
        )
        if list_data:
            self.assertGreaterEqual(list_data["total"], 5)

        required_content_keys = {
            "lecture": "sections",
            "exercise": "question_bank",
            "mindmap": "root",
            "slide": "slides",
            "code_lab": "starter_code",
        }
        for resource_id in resource_ids:
            detail = self._check(
                f"resource detail {resource_id}",
                "GET",
                f"/api/resource/{resource_id}",
                required_data_keys=["resource_id", "type", "content", "audit_status"],
            )
            if detail:
                resource_type = detail["type"]
                self.assertIn(required_content_keys[resource_type], detail["content"])
                self.assertIn("rag_context", detail["content"])

        if resource_ids:
            audit_data = self._check(
                "audit resource",
                "POST",
                f"/api/audit/resource/{resource_ids[0]}",
                json_body={"auditor_id": self.teacher_id, "strictness": "standard"},
                required_data_keys=[
                    "audit_id",
                    "resource_id",
                    "status",
                    "risk_level",
                    "issues",
                    "citations",
                    "hallucination_checks",
                ],
            )
            if audit_data:
                self.assertIn(audit_data["status"], ["approved", "rejected"])
                self.assertIn(audit_data["risk_level"], ["low", "medium", "high"])

            audited_detail = self._check(
                "resource detail after audit",
                "GET",
                f"/api/resource/{resource_ids[0]}",
                required_data_keys=["audit_status"],
            )
            if audited_detail and audit_data:
                self.assertEqual(audited_detail["audit_status"], audit_data["status"])

        tutor_data = self._check(
            "classroom ask",
            "POST",
            "/api/classroom/ask",
            json_body={
                "user_id": self.user_id,
                "course_id": self.course_id,
                "knowledge_point_id": self.knowledge_point_id,
                "question": (
                    "Why is BFS suitable for shortest paths in unweighted graphs? "
                    "Explain using the queue and visited set."
                ),
            },
            required_data_keys=[
                "session_id",
                "answer",
                "guidance_steps",
                "follow_up_questions",
                "personalization",
            ],
        )
        if tutor_data:
            self.assertTrue(tutor_data["answer"])

        classroom_data = self._check(
            "classroom generate",
            "POST",
            "/api/classroom/generate",
            json_body={
                "user_id": self.user_id,
                "course_id": self.course_id,
                "knowledge_point_id": self.knowledge_point_id,
                "topic": "BFS breadth-first search",
                "source_document_ids": [],
            },
            required_data_keys=["session_id", "title", "status", "scene_count", "scene_types"],
        )
        if classroom_data:
            classroom_session_id = classroom_data["session_id"]
            self.assertEqual(classroom_data["status"], "completed")
            self.assertGreaterEqual(classroom_data["scene_count"], 5)
            for scene_type in [
                "teacher_explain",
                "classmate_question",
                "whiteboard",
                "quiz",
            ]:
                self.assertIn(scene_type, classroom_data["scene_types"])

        if classroom_session_id:
            classroom_detail = self._check(
                "classroom detail",
                "GET",
                f"/api/classroom/{classroom_session_id}",
                required_data_keys=["title", "learning_goals", "agents", "scenes"],
            )
            if classroom_detail:
                self.assertGreaterEqual(len(classroom_detail["scenes"]), 5)

        if resource_ids:
            deleted = self._check(
                "resource delete",
                "DELETE",
                f"/api/resource/{resource_ids[-1]}",
                required_data_keys=["resource_id", "deleted"],
            )
            if deleted:
                self.assertTrue(deleted["deleted"])

            self._check(
                "resource deleted 404",
                "GET",
                f"/api/resource/{resource_ids[-1]}",
                expected_status=404,
                expected_code=404,
            )

        self._check(
            "resource not found",
            "GET",
            "/api/resource/not-exist",
            expected_status=404,
            expected_code=404,
        )
        self._check(
            "task not found",
            "GET",
            "/api/task/not-exist",
            expected_status=404,
            expected_code=404,
        )
        self._check(
            "classroom not found",
            "GET",
            "/api/classroom/not-exist",
            expected_status=404,
            expected_code=404,
        )
        self._check(
            "validation error",
            "POST",
            "/api/resource/generate",
            json_body={"user_id": self.user_id},
            expected_status=422,
            wrapped_response=False,
        )

        print("\nMEMBER_C_LIVE_API_RESULTS")
        print(json.dumps(self.results, ensure_ascii=False, indent=2))

    def _check(
        self,
        name: str,
        method: str,
        path: str,
        *,
        json_body: dict | None = None,
        params: dict | None = None,
        expected_status: int = 200,
        expected_code: int = 0,
        required_data_keys: list[str] | None = None,
        wrapped_response: bool = True,
        timeout_hint: str | None = None,
    ) -> dict | None:
        start = time.perf_counter()
        response = self.client.request(method, path, json=json_body, params=params)
        elapsed_ms = round((time.perf_counter() - start) * 1000)

        result = {
            "step": name,
            "method": method,
            "path": path,
            "status_code": response.status_code,
            "elapsed_ms": elapsed_ms,
        }
        if timeout_hint:
            result["note"] = timeout_hint

        try:
            payload = response.json()
        except ValueError:
            payload = {"raw": response.text[:500]}

        if response.status_code != expected_status:
            result["payload"] = _safe_payload(payload)
            self.results.append(result)
            self.fail(
                f"{name} expected HTTP {expected_status}, got "
                f"{response.status_code}: {_safe_payload(payload)}"
            )

        if not wrapped_response:
            self.results.append(result)
            return None

        if payload.get("code") != expected_code:
            result["payload"] = _safe_payload(payload)
            self.results.append(result)
            self.fail(
                f"{name} expected code {expected_code}, got "
                f"{payload.get('code')}: {_safe_payload(payload)}"
            )

        data = payload.get("data")
        if required_data_keys:
            missing = [key for key in required_data_keys if key not in data]
            if missing:
                result["payload"] = _safe_payload(payload)
                self.results.append(result)
                self.fail(f"{name} missing data keys: {missing}")

        self.results.append(result)
        return data


def _safe_payload(payload):
    text = json.dumps(payload, ensure_ascii=False, default=str)
    if len(text) > 1500:
        text = f"{text[:1500]}..."
    return text


if __name__ == "__main__":
    unittest.main()
