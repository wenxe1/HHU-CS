import asyncio
import json
import sys
import time
import unittest
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

load_dotenv(PROJECT_DIR / ".env")


class BackendAIClientSmokeTest(unittest.TestCase):
    def test_backend_ai_client_paths(self):
        results = asyncio.run(_check_backend_client())
        print("\nBACKEND_AI_CLIENT_SMOKE_RESULTS")
        print(json.dumps(results, ensure_ascii=False, indent=2))

        failures = [item for item in results if not item["ok"]]
        self.assertEqual(failures, [])


async def _check_backend_client() -> list[dict]:
    from app.services.ai_client import OpenAICompatibleAIClient

    client = OpenAICompatibleAIClient()
    return [
        await _check_generate_json(client, "text generation", use_reasoning=False),
        await _check_generate_json(client, "reasoning generation", use_reasoning=True),
        await _check_embedding(client),
    ]


async def _check_generate_json(client, label: str, *, use_reasoning: bool) -> dict:
    started = time.perf_counter()
    try:
        payload = await client.generate_json(
            agent_name=f"{label} smoke",
            system_prompt="You are a backend API smoke test.",
            user_prompt='Return {"ok": true}.',
            response_schema={"ok": "boolean"},
            use_reasoning=use_reasoning,
        )
        return {
            "label": label,
            "ok": payload.get("ok") is True,
            "elapsed_ms": _elapsed_ms(started),
            "sample": payload,
        }
    except Exception as exc:
        return {
            "label": label,
            "ok": False,
            "elapsed_ms": _elapsed_ms(started),
            "error": str(exc),
        }


async def _check_embedding(client) -> dict:
    started = time.perf_counter()
    try:
        embeddings = await client.embed_texts(["EduAgent Studio embedding smoke test."])
        dimension = len(embeddings[0]) if embeddings else 0
        return {
            "label": "embedding",
            "ok": dimension > 0,
            "elapsed_ms": _elapsed_ms(started),
            "dimension": dimension,
        }
    except Exception as exc:
        return {
            "label": "embedding",
            "ok": False,
            "elapsed_ms": _elapsed_ms(started),
            "error": str(exc),
        }


def _elapsed_ms(started: float) -> int:
    return round((time.perf_counter() - started) * 1000)


if __name__ == "__main__":
    unittest.main()
