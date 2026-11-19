import asyncio
import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient

from app.api.dependencies import get_auth_service
from app.main import app
from app.services.auth_service import AuthService, InMemoryAuthRepository


class AuthApiTest(unittest.TestCase):
    def setUp(self):
        self.repository = InMemoryAuthRepository()
        app.dependency_overrides[get_auth_service] = lambda: AuthService(
            self.repository,
        )
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_register_stores_hashed_password_and_login_succeeds(self):
        register_response = self.client.post(
            "/api/auth/register",
            json={
                "username": "student01",
                "password": "secret123",
                "confirm_password": "secret123",
            },
        )

        self.assertEqual(register_response.status_code, 200)
        register_data = register_response.json()["data"]
        self.assertEqual(register_data["username"], "student01")
        self.assertNotIn("password", register_data)

        stored_user = asyncio.run(
            self.repository.find_user_by_username("student01")
        )
        self.assertIsNotNone(stored_user)
        self.assertNotEqual(stored_user.password_hash, "secret123")
        self.assertTrue(stored_user.password_hash.startswith("pbkdf2_sha256$"))

        login_response = self.client.post(
            "/api/auth/login",
            json={"username": "student01", "password": "secret123"},
        )

        self.assertEqual(login_response.status_code, 200)
        self.assertEqual(login_response.json()["data"]["user_id"], register_data["user_id"])

    def test_register_rejects_duplicate_username(self):
        body = {
            "username": "student01",
            "password": "secret123",
            "confirm_password": "secret123",
        }
        self.assertEqual(self.client.post("/api/auth/register", json=body).status_code, 200)

        duplicate_response = self.client.post("/api/auth/register", json=body)

        self.assertEqual(duplicate_response.status_code, 409)
        self.assertEqual(duplicate_response.json()["code"], 409)

    def test_login_rejects_wrong_password(self):
        self.client.post(
            "/api/auth/register",
            json={
                "username": "student01",
                "password": "secret123",
                "confirm_password": "secret123",
            },
        )

        login_response = self.client.post(
            "/api/auth/login",
            json={"username": "student01", "password": "wrong-password"},
        )

        self.assertEqual(login_response.status_code, 401)
        self.assertEqual(login_response.json()["code"], 401)


if __name__ == "__main__":
    unittest.main()
