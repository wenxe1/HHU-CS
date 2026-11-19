import hashlib
import hmac
import secrets
from datetime import UTC, datetime
from typing import Protocol
from uuid import uuid4

from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel
from pymongo.errors import DuplicateKeyError

from app.schemas.auth import AuthLoginRequest, AuthRegisterRequest


PASSWORD_HASH_ALGORITHM = "pbkdf2_sha256"
PASSWORD_HASH_ITERATIONS = 120_000


class UsernameAlreadyExists(RuntimeError):
    pass


class InvalidCredentials(RuntimeError):
    pass


class PasswordConfirmationMismatch(RuntimeError):
    pass


class AuthUser(BaseModel):
    user_id: str
    username: str
    username_key: str
    password_hash: str
    created_at: datetime


class AuthRepository(Protocol):
    async def find_user_by_username(self, username: str) -> AuthUser | None:
        ...

    async def save_user(self, user: AuthUser) -> None:
        ...


class MongoAuthRepository:
    def __init__(self, database: AsyncIOMotorDatabase):
        self._users = database["auth_users"]

    async def find_user_by_username(self, username: str) -> AuthUser | None:
        document = await self._users.find_one(
            {"username_key": _username_key(username)},
            {"_id": False},
        )
        if document is None:
            return None
        return AuthUser.model_validate(document)

    async def save_user(self, user: AuthUser) -> None:
        await self._users.create_index("username_key", unique=True)
        try:
            await self._users.insert_one(user.model_dump(mode="python"))
        except DuplicateKeyError as exc:
            raise UsernameAlreadyExists from exc


class InMemoryAuthRepository:
    def __init__(self):
        self._users: dict[str, AuthUser] = {}

    async def find_user_by_username(self, username: str) -> AuthUser | None:
        user = self._users.get(_username_key(username))
        return user.model_copy(deep=True) if user else None

    async def save_user(self, user: AuthUser) -> None:
        if user.username_key in self._users:
            raise UsernameAlreadyExists
        self._users[user.username_key] = user.model_copy(deep=True)


class AuthService:
    def __init__(self, repository: AuthRepository):
        self._repository = repository

    async def register(self, request: AuthRegisterRequest) -> dict[str, str]:
        username = _normalize_username(request.username)
        password = request.password.strip()
        confirm_password = request.confirm_password.strip()

        if password != confirm_password:
            raise PasswordConfirmationMismatch

        existing_user = await self._repository.find_user_by_username(username)
        if existing_user is not None:
            raise UsernameAlreadyExists

        user = AuthUser(
            user_id=str(uuid4()),
            username=username,
            username_key=_username_key(username),
            password_hash=hash_password(password),
            created_at=datetime.now(UTC),
        )
        await self._repository.save_user(user)
        return _to_response(user)

    async def login(self, request: AuthLoginRequest) -> dict[str, str]:
        username = _normalize_username(request.username)
        password = request.password.strip()
        user = await self._repository.find_user_by_username(username)

        if user is None or not verify_password(password, user.password_hash):
            raise InvalidCredentials

        return _to_response(user)


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PASSWORD_HASH_ITERATIONS,
    ).hex()
    return (
        f"{PASSWORD_HASH_ALGORITHM}$"
        f"{PASSWORD_HASH_ITERATIONS}$"
        f"{salt}$"
        f"{digest}"
    )


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations_text, salt, digest = stored_hash.split("$", 3)
        iterations = int(iterations_text)
    except ValueError:
        return False

    if algorithm != PASSWORD_HASH_ALGORITHM:
        return False

    candidate = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    ).hex()
    return hmac.compare_digest(candidate, digest)


def _normalize_username(username: str) -> str:
    return username.strip()


def _username_key(username: str) -> str:
    return _normalize_username(username).casefold()


def _to_response(user: AuthUser) -> dict[str, str]:
    return {"user_id": user.user_id, "username": user.username}
