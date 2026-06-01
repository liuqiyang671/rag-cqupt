from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.main import app


class FakeRAGService:
    def __init__(self, **_kwargs):
        pass

    async def ask_stream(self, _question: str, session_id: int | None = None):
        yield 'data: {"type":"metadata","retrieved_context":[],"model_provider":"mock","session_id":1,"conversation_summary":""}\n\n'
        yield 'data: {"type":"chunk","content":"公开回答"}\n\n'
        yield 'data: {"type":"done","qa_record_id":1,"session_id":1,"conversation_summary":"摘要"}\n\n'


def test_stream_qa_allows_public_access_without_token(monkeypatch):
    def override_get_db():
        yield object()

    monkeypatch.setattr("app.api.routes.qa.RAGService", FakeRAGService)
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_settings] = lambda: Settings(MODEL_PROVIDER="mock", EMBEDDING_PROVIDER="mock")

    client = TestClient(app)
    response = client.post("/api/qa/ask/stream", json={"question": "校园卡怎么挂失？"})

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "公开回答" in response.text
