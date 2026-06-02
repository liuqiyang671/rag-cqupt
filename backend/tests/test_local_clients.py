import asyncio

import httpx
import pytest

from app.core.ai_errors import EmbeddingProviderError, ModelProviderError
from app.services.embedding.local_embedding import LocalEmbeddingClient
from app.services.llm.local_client import LocalLLMClient


class FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200):
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")
        return None

    def json(self) -> dict:
        return self.payload


def test_local_llm_client_ignores_proxy_environment(monkeypatch):
    captured_kwargs = {}
    captured_json = {}

    class FakeAsyncClient:
        def __init__(self, **kwargs):
            captured_kwargs.update(kwargs)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, *_args, **kwargs):
            captured_json.update(kwargs["json"])
            return FakeResponse({"message": {"content": "你好"}})

    monkeypatch.setattr("app.services.llm.local_client.httpx.AsyncClient", FakeAsyncClient)

    result = asyncio.run(LocalLLMClient("http://127.0.0.1:11434", "qwen3.5:9b").chat([]))

    assert result == "你好"
    assert captured_kwargs["trust_env"] is False
    assert captured_json["think"] is False
    assert captured_json["options"]["num_predict"] == 384


def test_local_embedding_client_ignores_proxy_environment(monkeypatch):
    captured_kwargs = {}

    class FakeAsyncClient:
        def __init__(self, **kwargs):
            captured_kwargs.update(kwargs)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, *_args, **_kwargs):
            return FakeResponse({"embedding": [0.1, 0.2, 0.3]})

    monkeypatch.setattr("app.services.embedding.local_embedding.httpx.AsyncClient", FakeAsyncClient)

    result = asyncio.run(LocalEmbeddingClient("http://127.0.0.1:11434", "nomic-embed-text", 3).embed("你好"))

    assert result == [0.1, 0.2, 0.3]
    assert captured_kwargs["trust_env"] is False


def test_local_embedding_client_raises_when_model_is_unavailable(monkeypatch):
    class FakeAsyncClient:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, *_args, **_kwargs):
            return FakeResponse({"error": "model not found"}, status_code=404)

    monkeypatch.setattr("app.services.embedding.local_embedding.httpx.AsyncClient", FakeAsyncClient)

    with pytest.raises(EmbeddingProviderError, match="本地 Embedding 模型不可用"):
        asyncio.run(LocalEmbeddingClient("http://127.0.0.1:11434", "missing-embedding", 4096).embed("你好"))


def test_local_embedding_client_raises_when_dimension_mismatches(monkeypatch):
    class FakeAsyncClient:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, *_args, **_kwargs):
            return FakeResponse({"embedding": [0.1, 0.2, 0.3]})

    monkeypatch.setattr("app.services.embedding.local_embedding.httpx.AsyncClient", FakeAsyncClient)

    with pytest.raises(EmbeddingProviderError, match="需要重新构建知识库向量"):
        asyncio.run(LocalEmbeddingClient("http://127.0.0.1:11434", "qwen3-embedding:8b-fp16", 4096).embed("你好"))


def test_local_llm_client_raises_when_model_is_unavailable(monkeypatch):
    class FakeAsyncClient:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, *_args, **_kwargs):
            return FakeResponse({"error": "model not found"}, status_code=404)

    monkeypatch.setattr("app.services.llm.local_client.httpx.AsyncClient", FakeAsyncClient)

    with pytest.raises(ModelProviderError, match="本地问答模型不可用"):
        asyncio.run(LocalLLMClient("http://127.0.0.1:11434", "missing-model").chat([]))
