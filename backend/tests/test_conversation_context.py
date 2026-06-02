import asyncio

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models import ConversationSession, Feedback, KnowledgeBase, QARecord, User  # noqa: F401
from app.services.qa_service import create_qa_record
from app.services.rag_service import RAGService, build_prompt


class StaticEmbeddingClient:
    async def embed(self, _text: str) -> list[float]:
        return [0.1, 0.2, 0.3]


class ScriptedLLMClient:
    def __init__(self, responses: list[str]):
        self.responses = responses
        self.prompts: list[str] = []

    async def chat(self, messages: list[dict[str, str]]) -> str:
        self.prompts.append(messages[-1]["content"])
        return self.responses.pop(0)


def _db_session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    return TestingSessionLocal()


def test_build_prompt_includes_summary_recent_turns_question_and_knowledge():
    prompt = build_prompt(
        question="我现在要怎么续借？",
        context_items=[
            {
                "title": "图书续借与逾期处理",
                "category": "图书馆服务",
                "content": "未被他人预约且未超过续借限制的图书，可通过图书馆系统办理续借。",
                "source": "图书馆服务指南",
                "citation_index": 1,
                "relevance_score": 0.92,
                "match_reason": "分类匹配、关键词命中、语义相似",
            }
        ],
        conversation_summary="用户此前主要咨询图书馆借阅证件和借阅权限。",
        recent_turns=[
            {"question": "借书要带什么？", "answer": "需要本人校园卡或统一身份认证账号。"},
            {"question": "可以借几本？", "answer": "不同读者类型可借册数不同。"},
        ],
    )

    assert "会话摘要" in prompt
    assert "用户此前主要咨询图书馆借阅证件和借阅权限。" in prompt
    assert "最近 3 轮对话" in prompt
    assert "用户：借书要带什么？" in prompt
    assert "助手：不同读者类型可借册数不同。" in prompt
    assert "当前问题：\n我现在要怎么续借？" in prompt
    assert "知识库内容" in prompt
    assert "图书续借与逾期处理" in prompt


def test_rag_service_uses_existing_session_summary_and_recent_three_turns(tmp_path, monkeypatch):
    db = _db_session(tmp_path)
    try:
        session = ConversationSession(summary="用户在持续咨询图书馆借阅服务。")
        db.add(session)
        db.commit()
        db.refresh(session)
        create_qa_record(db, "第 1 轮问题", "第 1 轮回答", [], "local", session_id=session.id)
        create_qa_record(db, "第 2 轮问题", "第 2 轮回答", [], "local", session_id=session.id)
        create_qa_record(db, "第 3 轮问题", "第 3 轮回答", [], "local", session_id=session.id)
        create_qa_record(db, "第 4 轮问题", "第 4 轮回答", [], "local", session_id=session.id)

        def fake_retrieve(_db, question, _embedding, top_k):
            assert question == "我现在要怎么续借？"
            assert top_k == 3
            return [
                {
                    "id": 1,
                    "title": "图书续借与逾期处理",
                    "category": "图书馆服务",
                    "content": "未被他人预约且未超过续借限制的图书，可以办理续借。",
                    "source": "图书馆服务指南",
                    "citation_index": 1,
                    "relevance_score": 0.9,
                    "match_reason": "分类匹配、关键词命中、语义相似",
                }
            ]

        monkeypatch.setattr("app.services.rag_service.retrieve_hybrid_knowledge", fake_retrieve)
        llm_client = ScriptedLLMClient(["当前回答。引用来源：[1] 图书续借与逾期处理 - 图书馆服务指南", "更新后的会话摘要"])
        service = RAGService(
            db=db,
            embedding_client=StaticEmbeddingClient(),
            llm_client=llm_client,
            model_provider="local",
            top_k=3,
            enable_query_rewriting=False,
            enable_query_decomposition=False,
        )

        result = asyncio.run(service.ask("我现在要怎么续借？", session_id=session.id))

        answer_prompt = llm_client.prompts[0]
        assert result["session_id"] == session.id
        assert result["conversation_summary"] == "更新后的会话摘要"
        assert "用户在持续咨询图书馆借阅服务。" in answer_prompt
        assert "第 1 轮问题" not in answer_prompt
        assert "第 2 轮问题" in answer_prompt
        assert "第 3 轮问题" in answer_prompt
        assert "第 4 轮问题" in answer_prompt
        assert "当前问题：\n我现在要怎么续借？" in answer_prompt
        assert "图书续借与逾期处理" in answer_prompt

        saved_record = db.get(QARecord, result["qa_record_id"])
        assert saved_record is not None
        assert saved_record.session_id == session.id
    finally:
        db.close()
