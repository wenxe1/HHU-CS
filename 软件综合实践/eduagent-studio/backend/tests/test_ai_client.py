import sys
import unittest
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib.error import HTTPError

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.services.ai_client import (
    AIConfigurationError,
    AIServiceError,
    OpenAICompatibleAIClient,
)


class FakeOpenAIClient:
    def __init__(self):
        self.chat_calls = []
        self.embedding_calls = []
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=self._create_chat_completion)
        )
        self.embeddings = SimpleNamespace(create=self._create_embedding)

    async def _create_chat_completion(self, **kwargs):
        self.chat_calls.append(kwargs)
        if kwargs.get("stream"):
            async def stream_response():
                for content in ("first ", "second"):
                    yield SimpleNamespace(
                        choices=[
                            SimpleNamespace(
                                delta=SimpleNamespace(content=content),
                            )
                        ]
                    )

            return stream_response()
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content='{"ok": true}'),
                )
            ]
        )

    async def _create_embedding(self, **kwargs):
        self.embedding_calls.append(kwargs)
        return SimpleNamespace(
            data=[SimpleNamespace(embedding=[1.0, 2.0]) for _ in kwargs["input"]]
        )


class OpenAICompatibleAIClientTest(unittest.IsolatedAsyncioTestCase):
    async def test_selects_default_and_reasoning_chat_models(self):
        fake_client = FakeOpenAIClient()
        client_requests = []
        ai_client = OpenAICompatibleAIClient(
            text_api_key="text-key",
            text_base_url="https://text.example/v1",
            model="simple-model",
            reasoning_api_key="reasoning-key",
            reasoning_base_url="https://reasoning.example/v1",
            reasoning_model="reasoning-model",
            embedding_model="embedding-model",
        )
        ai_client._get_client = lambda api_key, base_url, purpose: client_requests.append(
            (api_key, base_url, purpose)
        ) or fake_client

        await ai_client.generate_json(
            agent_name="Simple Agent",
            system_prompt="system",
            user_prompt="user",
            response_schema={"ok": "boolean"},
        )
        await ai_client.generate_json(
            agent_name="Reasoning Agent",
            system_prompt="system",
            user_prompt="user",
            response_schema={"ok": "boolean"},
            use_reasoning=True,
        )

        self.assertEqual(
            [call["model"] for call in fake_client.chat_calls],
            ["simple-model", "reasoning-model"],
        )
        self.assertEqual(
            client_requests,
            [
                ("text-key", "https://text.example/v1", "text generation"),
                (
                    "reasoning-key",
                    "https://reasoning.example/v1",
                    "reasoning generation",
                ),
            ],
        )

    async def test_uses_embedding_model_for_embeddings(self):
        ai_client = OpenAICompatibleAIClient(
            embedding_app_id="embedding-app",
            embedding_api_key="embedding-key",
            embedding_api_secret="embedding-secret",
            embedding_base_url="https://embedding.example/v1",
            model="simple-model",
            reasoning_model="reasoning-model",
            embedding_model="embedding-model",
        )

        with patch("app.services.ai_client.XUNFEI_EMBEDDING_MIN_INTERVAL_SECONDS", 0):
            with patch(
                "app.services.ai_client._request_xunfei_embedding",
                return_value=[1.0, 2.0],
            ) as request_embedding:
                embeddings = await ai_client.embed_texts(["first", "second"])

        self.assertEqual(embeddings, [[1.0, 2.0], [1.0, 2.0]])
        self.assertEqual(request_embedding.call_count, 2)
        self.assertEqual(
            request_embedding.call_args_list[0].kwargs,
            {
                "base_url": "https://embedding.example/v1",
                "app_id": "embedding-app",
                "api_key": "embedding-key",
                "api_secret": "embedding-secret",
                "text": "first",
                "domain": "para",
            },
        )

    async def test_streams_text_deltas_from_chat_model(self):
        fake_client = FakeOpenAIClient()
        ai_client = OpenAICompatibleAIClient(
            text_api_key="text-key",
            text_base_url="https://text.example/v1",
            model="simple-model",
        )
        ai_client._get_client = lambda *_args: fake_client

        deltas = [
            delta
            async for delta in ai_client.stream_text(
                agent_name="Streaming Agent",
                system_prompt="system",
                user_prompt="user",
            )
        ]

        self.assertEqual(deltas, ["first ", "second"])
        self.assertTrue(fake_client.chat_calls[0]["stream"])
        self.assertEqual(fake_client.chat_calls[0]["model"], "simple-model")

    @patch.dict(
        "os.environ",
        {
            "AI_DEEPSEEK_API_KEY": "deepseek-key",
            "AI_DEEPSEEK_BASE_URL": "https://deepseek.example/v1",
            "AI_DEEPSEEK_MODEL": "deepseek-chat-model",
            "AI_DEEPSEEK_REASONING_API_KEY": "deepseek-reasoning-key",
            "AI_DEEPSEEK_REASONING_BASE_URL": "https://deepseek.example/v1",
            "AI_DEEPSEEK_REASONING_MODEL": "deepseek-reasoning-model",
        },
    )
    async def test_uses_deepseek_generation_environment_by_default(self):
        fake_client = FakeOpenAIClient()
        client_requests = []
        ai_client = OpenAICompatibleAIClient()
        ai_client._get_client = lambda api_key, base_url, purpose: client_requests.append(
            (api_key, base_url, purpose)
        ) or fake_client

        await ai_client.generate_json(
            agent_name="DeepSeek Chat Agent",
            system_prompt="system",
            user_prompt="user",
            response_schema={"ok": "boolean"},
        )
        await ai_client.generate_json(
            agent_name="DeepSeek Reasoning Agent",
            system_prompt="system",
            user_prompt="user",
            response_schema={"ok": "boolean"},
            use_reasoning=True,
        )

        self.assertEqual(
            [call["model"] for call in fake_client.chat_calls],
            ["deepseek-chat-model", "deepseek-reasoning-model"],
        )
        self.assertEqual(
            client_requests,
            [
                (
                    "deepseek-key",
                    "https://deepseek.example/v1",
                    "text generation",
                ),
                (
                    "deepseek-reasoning-key",
                    "https://deepseek.example/v1",
                    "reasoning generation",
                ),
            ],
        )

    async def test_retries_transient_xunfei_embedding_license_error(self):
        ai_client = OpenAICompatibleAIClient(
            embedding_app_id="embedding-app",
            embedding_api_key="embedding-key",
            embedding_api_secret="embedding-secret",
            embedding_base_url="https://embedding.example/v1",
            embedding_model="embedding-model",
        )

        with patch("app.services.ai_client.XUNFEI_EMBEDDING_MIN_INTERVAL_SECONDS", 0):
            with patch("app.services.ai_client.XUNFEI_EMBEDDING_RETRY_DELAYS", (0.0,)):
                with patch(
                    "app.services.ai_client._request_xunfei_embedding",
                    side_effect=[
                        AIServiceError(
                            'xunfei embedding HTTP 500 Internal Server Error: '
                            '{"header":{"code":11202,"message":"licc failed"}}'
                        ),
                        [1.0, 2.0],
                    ],
                ) as request_embedding:
                    embeddings = await ai_client.embed_texts(["chunk"])

        self.assertEqual(embeddings, [[1.0, 2.0]])
        self.assertEqual(request_embedding.call_count, 2)
        self.assertEqual(
            request_embedding.call_args_list[0].kwargs,
            {
                "base_url": "https://embedding.example/v1",
                "app_id": "embedding-app",
                "api_key": "embedding-key",
                "api_secret": "embedding-secret",
                "text": "chunk",
                "domain": "para",
            },
        )

    async def test_embedding_http_error_includes_status_and_body(self):
        ai_client = OpenAICompatibleAIClient(
            embedding_app_id="embedding-app",
            embedding_api_key="embedding-key",
            embedding_api_secret="embedding-secret",
            embedding_base_url="https://embedding.example/v1",
            embedding_model="embedding-model",
        )
        http_error = HTTPError(
            "https://embedding.example/v1",
            413,
            "Payload Too Large",
            {},
            BytesIO(b'{"message":"text too long"}'),
        )

        with patch("app.services.ai_client.XUNFEI_EMBEDDING_MIN_INTERVAL_SECONDS", 0):
            with patch("app.services.ai_client.urlopen", side_effect=http_error):
                with self.assertRaisesRegex(
                    Exception,
                    "HTTP 413 Payload Too Large.*text too long",
                ):
                    await ai_client.embed_texts(["too long"])

    async def test_reasoning_model_does_not_fallback_to_text_model(self):
        ai_client = OpenAICompatibleAIClient(
            text_api_key="text-key",
            text_base_url="https://text.example/v1",
            model="simple-model",
            reasoning_api_key="reasoning-key",
            reasoning_base_url="https://reasoning.example/v1",
            reasoning_model="",
        )

        with self.assertRaisesRegex(AIConfigurationError, "AI_DEEPSEEK_REASONING_MODEL"):
            await ai_client.generate_json(
                agent_name="Reasoning Agent",
                system_prompt="system",
                user_prompt="user",
                response_schema={"ok": "boolean"},
                use_reasoning=True,
            )


if __name__ == "__main__":
    unittest.main()
