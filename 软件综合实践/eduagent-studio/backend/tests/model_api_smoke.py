import asyncio
import json
import os
import sys
import time
import unittest
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

load_dotenv(PROJECT_DIR / ".env")


class ModelApiSmokeTest(unittest.TestCase):
    def test_configured_models_are_reachable(self):
        results = asyncio.run(_check_models())
        print("\nMODEL_API_SMOKE_RESULTS")
        print(json.dumps(results, ensure_ascii=False, indent=2))

        failures = [item for item in results if not item["ok"]]
        self.assertEqual(failures, [])


async def _check_models() -> list[dict]:
    results = []
    results.append(
        await _check_chat_model(
            label="AI_DEEPSEEK_MODEL",
            api_key=os.getenv("AI_DEEPSEEK_API_KEY"),
            base_url=os.getenv("AI_DEEPSEEK_BASE_URL"),
            model=os.getenv("AI_DEEPSEEK_MODEL"),
            prompt="Reply with exactly: OK",
        )
    )
    results.append(
        await _check_chat_model(
            label="AI_DEEPSEEK_REASONING_MODEL",
            api_key=os.getenv("AI_DEEPSEEK_REASONING_API_KEY"),
            base_url=os.getenv("AI_DEEPSEEK_REASONING_BASE_URL"),
            model=os.getenv("AI_DEEPSEEK_REASONING_MODEL"),
            prompt="What is 2 + 2? Reply with only the final number.",
        )
    )
    results.append(
        await _check_xunfei_embedding_model(
            label="AI_EMBEDDING_MODEL",
            app_id=os.getenv("AI_EMBEDDING_APP_ID"),
            base_url=os.getenv("AI_EMBEDDING_BASE_URL"),
            api_key=os.getenv("AI_EMBEDDING_API_KEY"),
            api_secret=os.getenv("AI_EMBEDDING_API_SECRET"),
            model=os.getenv("AI_EMBEDDING_MODEL"),
        )
    )
    return results


async def _check_chat_model(
    *,
    label: str,
    api_key: str | None,
    base_url: str | None,
    model: str | None,
    prompt: str,
) -> dict:
    config_error = _config_error(label, api_key, base_url, model)
    started = time.perf_counter()
    try:
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a concise API smoke test."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=512,
            stream=True,
        )
        content = ""
        async for chunk in response:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            content += getattr(delta, "content", None) or ""
        return {
            "label": label,
            "model": model,
            "ok": bool(content.strip()),
            "elapsed_ms": _elapsed_ms(started),
            "sample": content.strip()[:120],
        }
    except Exception as exc:
        return _failure(label, str(exc), model=model, started=started)


async def _check_xunfei_embedding_model(
    *,
    label: str,
    app_id: str | None,
    base_url: str | None,
    api_key: str | None,
    api_secret: str | None,
    model: str | None,
) -> dict:
    missing = []
    if not app_id:
        missing.append("AI_EMBEDDING_APP_ID")
    if not base_url:
        missing.append("AI_EMBEDDING_BASE_URL")
    if not api_key:
        missing.append("AI_EMBEDDING_API_KEY")
    if not api_secret:
        missing.append("AI_EMBEDDING_API_SECRET")
    if not model:
        missing.append("AI_EMBEDDING_MODEL")
    if missing:
        return _failure(label, f"missing config: {', '.join(missing)}", model=model)

    started = time.perf_counter()
    try:
        from app.services.ai_client import _request_xunfei_embedding

        embedding = await asyncio.to_thread(
            _request_xunfei_embedding,
            base_url=base_url,
            app_id=app_id,
            api_key=api_key,
            api_secret=api_secret,
            text="EduAgent Studio model API smoke test.",
            domain="para",
        )
        return {
            "label": label,
            "model": model,
            "ok": bool(embedding),
            "elapsed_ms": _elapsed_ms(started),
            "dimension": len(embedding),
        }
    except Exception as exc:
        return _failure(label, str(exc), model=model, started=started)


def _failure(
    label: str,
    message: str,
    *,
    model: str | None = None,
    started: float | None = None,
) -> dict:
    result = {
        "label": label,
        "model": model,
        "ok": False,
        "error": message,
    }
    if started is not None:
        result["elapsed_ms"] = _elapsed_ms(started)
    return result


def _config_error(
    label: str,
    api_key: str | None,
    base_url: str | None,
    model: str | None,
) -> dict | None:
    missing = []
    if not api_key:
        missing.append(f"{label.replace('MODEL', 'API_KEY')}")
    if not base_url:
        missing.append(f"{label.replace('MODEL', 'BASE_URL')}")
    if not model:
        missing.append(label)
    if missing:
        return _failure(label, f"missing config: {', '.join(missing)}", model=model)
    return None


def _elapsed_ms(started: float) -> int:
    return round((time.perf_counter() - started) * 1000)


if __name__ == "__main__":
    unittest.main()
