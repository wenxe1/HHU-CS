import asyncio
import base64
import hashlib
import hmac
import json
import os
import struct
from collections.abc import AsyncIterator
from datetime import datetime
from time import mktime
from typing import Any, Protocol, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
from wsgiref.handlers import format_date_time


class AIServiceError(RuntimeError):
    pass


class AIConfigurationError(AIServiceError):
    pass


XUNFEI_EMBEDDING_MIN_INTERVAL_SECONDS = 1.2
XUNFEI_EMBEDDING_RETRY_DELAYS = (1.2, 2.4)
_xunfei_embedding_lock = asyncio.Lock()
_xunfei_last_embedding_request_at = 0.0


class AIClient(Protocol):
    async def generate_json(
        self,
        agent_name: str,
        system_prompt: str,
        user_prompt: str,
        response_schema: dict[str, Any],
        use_reasoning: bool = False,
    ) -> dict[str, Any]:
        ...

    def stream_text(
        self,
        agent_name: str,
        system_prompt: str,
        user_prompt: str,
        use_reasoning: bool = False,
    ) -> AsyncIterator[str]:
        ...

    async def embed_texts(
        self,
        texts: Sequence[str],
        embedding_domain: str = "para",
    ) -> list[list[float]]:
        ...


class OpenAICompatibleAIClient:
    def __init__(
        self,
        text_api_key: str | None = None,
        text_base_url: str | None = None,
        model: str | None = None,
        reasoning_api_key: str | None = None,
        reasoning_base_url: str | None = None,
        reasoning_model: str | None = None,
        embedding_app_id: str | None = None,
        embedding_api_key: str | None = None,
        embedding_api_secret: str | None = None,
        embedding_base_url: str | None = None,
        embedding_model: str | None = None,
        text_env_prefix: str = "AI_DEEPSEEK",
        reasoning_env_prefix: str = "AI_DEEPSEEK_REASONING",
    ):
        self._text_env_prefix = text_env_prefix
        self._reasoning_env_prefix = reasoning_env_prefix
        self._text_api_key = _configured_value(
            text_api_key,
            f"{text_env_prefix}_API_KEY",
        )
        self._text_base_url = _configured_value(
            text_base_url,
            f"{text_env_prefix}_BASE_URL",
        )
        self._model = _configured_value(model, f"{text_env_prefix}_MODEL")
        self._reasoning_api_key = _configured_value(
            reasoning_api_key,
            f"{reasoning_env_prefix}_API_KEY",
        )
        self._reasoning_base_url = _configured_value(
            reasoning_base_url,
            f"{reasoning_env_prefix}_BASE_URL",
        )
        self._reasoning_model = _configured_value(
            reasoning_model,
            f"{reasoning_env_prefix}_MODEL",
        )
        self._embedding_app_id = _configured_value(
            embedding_app_id,
            "AI_EMBEDDING_APP_ID",
        )
        self._embedding_api_key = _configured_value(
            embedding_api_key,
            "AI_EMBEDDING_API_KEY",
        )
        self._embedding_api_secret = _configured_value(
            embedding_api_secret,
            "AI_EMBEDDING_API_SECRET",
        )
        self._embedding_base_url = _configured_value(
            embedding_base_url,
            "AI_EMBEDDING_BASE_URL",
        )
        self._embedding_model = _configured_value(
            embedding_model,
            "AI_EMBEDDING_MODEL",
        )
        self._clients = {}

    async def generate_json(
        self,
        agent_name: str,
        system_prompt: str,
        user_prompt: str,
        response_schema: dict[str, Any],
        use_reasoning: bool = False,
    ) -> dict[str, Any]:
        model, client = self._generation_client(use_reasoning)
        prompt = (
            f"{user_prompt}\n\n"
            "请严格返回一个 JSON object，不要使用 Markdown，不要输出解释文字。\n"
            f"JSON 字段要求：{json.dumps(response_schema, ensure_ascii=False)}"
        )
        prompt = (
            f"{user_prompt}\n\n"
            "Return only one valid JSON object. Do not use Markdown. "
            "Do not output explanations outside the JSON object.\n"
            f"Required JSON fields: {json.dumps(response_schema, ensure_ascii=False)}"
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.2,
                stream=False,
            )
            content = await _collect_chat_content(response)
        except Exception as exc:
            try:
                response = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.2,
                    stream=True,
                )
                content = await _collect_chat_content(response)
            except Exception as fallback_exc:
                raise AIServiceError(
                    f"{agent_name} AI call failed: {fallback_exc}"
                ) from fallback_exc
        if not content:
            raise AIServiceError(f"{agent_name} returned empty content")

        return _parse_json_object(content, agent_name)

    async def stream_text(
        self,
        agent_name: str,
        system_prompt: str,
        user_prompt: str,
        use_reasoning: bool = False,
    ) -> AsyncIterator[str]:
        model, client = self._generation_client(use_reasoning)
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                stream=True,
            )
            has_content = False
            async for chunk in response:
                if not chunk.choices:
                    continue
                content = getattr(chunk.choices[0].delta, "content", None)
                if content:
                    has_content = True
                    yield content
            if not has_content:
                raise AIServiceError(f"{agent_name} returned empty content")
        except AIServiceError:
            raise
        except Exception as exc:
            raise AIServiceError(f"{agent_name} AI stream failed: {exc}") from exc

    async def embed_texts(
        self,
        texts: Sequence[str],
        embedding_domain: str = "para",
    ) -> list[list[float]]:
        if not texts:
            return []

        app_id = _require_configured(
            self._embedding_app_id,
            "AI_EMBEDDING_APP_ID",
            "embedding",
        )
        api_key = _require_configured(
            self._embedding_api_key,
            "AI_EMBEDDING_API_KEY",
            "embedding",
        )
        api_secret = _require_configured(
            self._embedding_api_secret,
            "AI_EMBEDDING_API_SECRET",
            "embedding",
        )
        base_url = _require_configured(
            self._embedding_base_url,
            "AI_EMBEDDING_BASE_URL",
            "embedding",
        )
        try:
            return [
                await _request_xunfei_embedding_throttled(
                    base_url=base_url,
                    app_id=app_id,
                    api_key=api_key,
                    api_secret=api_secret,
                    text=text,
                    domain=embedding_domain,
                )
                for text in texts
            ]
        except Exception as exc:
            raise AIServiceError(f"embedding call failed: {exc}") from exc

    def _generation_client(self, use_reasoning: bool):
        if use_reasoning:
            model = _require_configured(
                self._reasoning_model,
                f"{self._reasoning_env_prefix}_MODEL",
                "reasoning generation",
            )
            client = self._get_client(
                self._reasoning_api_key,
                self._reasoning_base_url,
                "reasoning generation",
            )
            return model, client

        model = _require_configured(
            self._model,
            f"{self._text_env_prefix}_MODEL",
            "text generation",
        )
        client = self._get_client(
            self._text_api_key,
            self._text_base_url,
            "text generation",
        )
        return model, client

    def _get_client(self, api_key: str | None, base_url: str | None, purpose: str):
        env_prefix = (
            self._reasoning_env_prefix
            if purpose == "reasoning generation"
            else self._text_env_prefix
        )
        api_key = _require_configured(api_key, f"{env_prefix}_API_KEY", purpose)
        base_url = _require_configured(
            base_url,
            f"{env_prefix}_BASE_URL",
            purpose,
        )
        cache_key = (api_key, base_url)
        if cache_key not in self._clients:
            from openai import AsyncOpenAI

            kwargs: dict[str, str] = {"api_key": api_key}
            kwargs["base_url"] = base_url
            self._clients[cache_key] = AsyncOpenAI(**kwargs)
        return self._clients[cache_key]


def _configured_value(explicit_value: str | None, env_name: str) -> str | None:
    value = explicit_value if explicit_value is not None else os.getenv(env_name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _parse_json_object(content: str, agent_name: str) -> dict[str, Any]:
    try:
        value = json.loads(content)
    except json.JSONDecodeError:
        try:
            value = _loads_first_json_object(content)
        except json.JSONDecodeError as exc:
            raise AIServiceError(f"{agent_name} returned invalid JSON") from exc

    if not isinstance(value, dict):
        raise AIServiceError(f"{agent_name} returned non-object JSON")
    return value


async def _collect_chat_content(response) -> str:
    if hasattr(response, "__aiter__"):
        parts = []
        async for chunk in response:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            content = getattr(delta, "content", None)
            if content:
                parts.append(content)
        return "".join(parts)

    return response.choices[0].message.content or ""


def _loads_first_json_object(content: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    start = content.find("{")
    while start != -1:
        try:
            value, _ = decoder.raw_decode(content[start:])
        except json.JSONDecodeError:
            start = content.find("{", start + 1)
            continue
        if isinstance(value, dict):
            return value
        start = content.find("{", start + 1)
    raise json.JSONDecodeError("No JSON object found", content, 0)


async def _request_xunfei_embedding_throttled(
    *,
    base_url: str,
    app_id: str,
    api_key: str,
    api_secret: str,
    text: str,
    domain: str,
) -> list[float]:
    last_error: AIServiceError | None = None
    delays = (0.0, *XUNFEI_EMBEDDING_RETRY_DELAYS)
    for attempt, retry_delay in enumerate(delays):
        if retry_delay:
            await asyncio.sleep(retry_delay)
        try:
            async with _xunfei_embedding_lock:
                await _wait_for_xunfei_embedding_slot()
                return await asyncio.to_thread(
                    _request_xunfei_embedding,
                    base_url=base_url,
                    app_id=app_id,
                    api_key=api_key,
                    api_secret=api_secret,
                    text=text,
                    domain=domain,
                )
        except AIServiceError as exc:
            last_error = exc
            if attempt == len(delays) - 1 or not _is_retryable_xunfei_error(exc):
                raise

    raise last_error or AIServiceError("xunfei embedding request failed")


async def _wait_for_xunfei_embedding_slot() -> None:
    global _xunfei_last_embedding_request_at

    loop = asyncio.get_running_loop()
    now = loop.time()
    wait_seconds = (
        _xunfei_last_embedding_request_at
        + XUNFEI_EMBEDDING_MIN_INTERVAL_SECONDS
        - now
    )
    if wait_seconds > 0:
        await asyncio.sleep(wait_seconds)
    _xunfei_last_embedding_request_at = loop.time()


def _is_retryable_xunfei_error(exc: AIServiceError) -> bool:
    message = str(exc).lower()
    return (
        "licc failed" in message
        or "code\":11202" in message
        or "http 500" in message
        or "http 502" in message
        or "http 503" in message
        or "http 504" in message
    )


def _request_xunfei_embedding(
    *,
    base_url: str,
    app_id: str,
    api_key: str,
    api_secret: str,
    text: str,
    domain: str,
) -> list[float]:
    if domain not in {"query", "para"}:
        raise ValueError("embedding_domain must be query or para")

    body = {
        "header": {
            "app_id": app_id,
            "uid": "eduagent-studio",
            "status": 3,
        },
        "parameter": {
            "emb": {
                "domain": domain,
                "feature": {"encoding": "utf8"},
            }
        },
        "payload": {
            "messages": {
                "text": base64.b64encode(
                    json.dumps(
                        {"messages": [{"content": text, "role": "user"}]},
                        ensure_ascii=False,
                    ).encode("utf-8")
                ).decode("utf-8")
            }
        },
    }
    request = Request(
        _xunfei_signed_url(base_url, api_key, api_secret),
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"content-type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace").strip()
        reason = getattr(exc, "reason", exc.msg)
        message = f"xunfei embedding HTTP {exc.code} {reason}"
        if detail:
            message = f"{message}: {detail[:1000]}"
        raise AIServiceError(message) from exc
    except URLError as exc:
        raise AIServiceError(f"xunfei embedding request failed: {exc.reason}") from exc
    code = payload.get("header", {}).get("code")
    if code != 0:
        raise AIServiceError(f"xunfei embedding returned code {code}: {payload}")

    raw = base64.b64decode(payload["payload"]["feature"]["text"])
    if len(raw) % 4 != 0:
        raise AIServiceError("xunfei embedding returned invalid float32 payload")
    return [item[0] for item in struct.iter_unpack("<f", raw)]


def _xunfei_signed_url(base_url: str, api_key: str, api_secret: str) -> str:
    request_url = base_url if urlparse(base_url).path else f"{base_url.rstrip('/')}/"
    parsed = urlparse(request_url)
    if not parsed.scheme or not parsed.netloc:
        raise AIConfigurationError(
            "embedding AI is not configured. Set AI_EMBEDDING_BASE_URL."
        )

    date = format_date_time(mktime(datetime.now().timetuple()))
    signature_origin = (
        f"host: {parsed.netloc}\n"
        f"date: {date}\n"
        f"POST {parsed.path or '/'} HTTP/1.1"
    )
    signature = base64.b64encode(
        hmac.new(
            api_secret.encode("utf-8"),
            signature_origin.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
    ).decode("utf-8")
    authorization_origin = (
        f'api_key="{api_key}", algorithm="hmac-sha256", '
        f'headers="host date request-line", signature="{signature}"'
    )
    authorization = base64.b64encode(
        authorization_origin.encode("utf-8")
    ).decode("utf-8")
    return (
        f"{request_url}?"
        f"{urlencode({'host': parsed.netloc, 'date': date, 'authorization': authorization})}"
    )


def _require_configured(
    value: str | None,
    env_name: str,
    purpose: str,
) -> str:
    if not value:
        raise AIConfigurationError(f"{purpose} AI is not configured. Set {env_name}.")
    return value
