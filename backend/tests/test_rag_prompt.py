import asyncio
import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.ai_errors import EmbeddingProviderError
from app.core.database import Base
from app.models import Feedback, KnowledgeBase, QARecord, User  # noqa: F401
from app.services.rag_service import RAGService, build_casual_answer, build_prompt


class ExplodingEmbeddingClient:
    async def embed(self, _text: str) -> list[float]:
        raise AssertionError("casual greeting should not call embedding retrieval")


class ExplodingLLMClient:
    async def chat(self, _messages: list[dict[str, str]]) -> str:
        raise AssertionError("casual greeting should not call the LLM")


class FailingEmbeddingClient:
    async def embed(self, _text: str) -> list[float]:
        raise EmbeddingProviderError("Embedding 服务不可用，请检查本地模型。")


def test_build_prompt_includes_campus_rules_context_and_question():
    prompt = build_prompt(
        question="校园卡丢了怎么办？",
        context_items=[
            {
                "title": "校园卡挂失流程",
                "category": "校园卡服务",
                "content": "校园卡丢失后，学生可以通过校园卡服务平台办理挂失。",
                "source": "校园卡服务中心",
                "citation_index": 1,
                "relevance_score": 0.92,
                "match_reason": "分类匹配、关键词命中、语义相似",
            }
        ],
    )

    assert "你是高校校园服务智能问答助手" in prompt
    assert "当前知识库中没有找到明确依据" in prompt
    assert "[1] 校园卡挂失流程" in prompt
    assert "引用编号" in prompt
    assert "回答末尾列出引用来源" in prompt
    assert "校园卡丢了怎么办？" in prompt


def test_build_casual_answer_handles_greeting_without_rag_template():
    answer = build_casual_answer("你好")

    assert answer is not None
    assert "校园问答助手" in answer
    assert "可参考以下校内知识" not in answer


def test_build_casual_answer_does_not_match_service_question():
    assert build_casual_answer("校园卡丢了怎么办？") is None


def test_rag_service_answers_casual_greeting_without_retrieval_or_llm(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        service = RAGService(
            db=db,
            embedding_client=ExplodingEmbeddingClient(),
            llm_client=ExplodingLLMClient(),
            model_provider="local",
            top_k=5,
        )

        result = asyncio.run(service.ask("你好"))

        assert result["retrieved_context"] == []
        assert result["model_provider"] == "system"
        assert "校园问答助手" in result["answer"]
    finally:
        db.close()


def test_rag_service_stream_yields_error_event_for_ai_service_failure(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        service = RAGService(
            db=db,
            embedding_client=FailingEmbeddingClient(),
            llm_client=ExplodingLLMClient(),
            model_provider="local",
            top_k=5,
        )

        events = asyncio.run(_collect_stream_events(service.ask_stream("校园卡怎么挂失？")))

        assert events[0]["type"] == "error"
        assert "Embedding 服务不可用" in events[0]["message"]
    finally:
        db.close()


async def _collect_stream_events(stream):
    events = []
    async for chunk in stream:
        if chunk.startswith("data: "):
            events.append(json.loads(chunk[6:]))
    return events
