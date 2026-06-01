import asyncio

from app.services.embedding.local_embedding import LocalEmbeddingClient
from app.services.llm.local_client import LocalLLMClient


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def raise_for_status(self) -> None:
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
