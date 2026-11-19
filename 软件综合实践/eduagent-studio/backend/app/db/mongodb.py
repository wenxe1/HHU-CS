import os
from urllib.parse import urlparse

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase


load_dotenv()

_client: AsyncIOMotorClient | None = None


def _mongo_url() -> str:
    return (
        os.getenv("MONGODB_URL")
        or os.getenv("DATABASE_URL")
        or "mongodb://localhost:27017/eduagent_studio"
    )


def _database_name(url: str) -> str:
    configured = os.getenv("MONGODB_DB_NAME")
    if configured:
        return configured

    path = urlparse(url).path.strip("/")
    return path or "eduagent_studio"


def get_mongo_database() -> AsyncIOMotorDatabase:
    global _client

    url = _mongo_url()
    if not url.startswith(("mongodb://", "mongodb+srv://")):
        raise RuntimeError("DATABASE_URL must be a MongoDB URL for backend runtime")

    if _client is None:
        _client = AsyncIOMotorClient(url, serverSelectionTimeoutMS=3000)

    return _client[_database_name(url)]


async def close_mongo_client() -> None:
    global _client

    if _client is not None:
        _client.close()
        _client = None
