import asyncio
from collections import Counter

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.data.campus_seed import CAMPUS_KNOWLEDGE_CATEGORIES, CAMPUS_KNOWLEDGE_ITEMS
from app.models import ConversationSession, KnowledgeBase, QARecord, User
from app.services.embedding.base import EmbeddingClient


class CountingEmbeddingClient(EmbeddingClient):
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def embed(self, text: str) -> list[float]:
        self.calls.append(text)
        return [float(len(self.calls))] * 4096


def _build_test_db(tmp_path) -> tuple[Session, sessionmaker]:
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False})
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    return testing_session_local(), testing_session_local


def _count(db: Session, model: type[object]) -> int:
    return db.scalar(select(func.count()).select_from(model)) or 0


def test_complete_rag_seed_data_has_exact_service_coverage():
    counts = Counter(item["category"] for item in CAMPUS_KNOWLEDGE_ITEMS)

    assert len(CAMPUS_KNOWLEDGE_CATEGORIES) == 9
    assert len(CAMPUS_KNOWLEDGE_ITEMS) == 900
    assert all(counts[category] == 100 for category in CAMPUS_KNOWLEDGE_CATEGORIES)


def test_complete_rag_loader_is_idempotent_and_updates_existing_items(tmp_path):
    from app.scripts.load_complete_rag_data import load_complete_rag_data

    db, _ = _build_test_db(tmp_path)
    embedding_client = CountingEmbeddingClient()
    try:
        first_result = asyncio.run(load_complete_rag_data(db, embedding_client, reset_knowledge=False))

        assert first_result.created_count == 900
        assert first_result.updated_count == 0
        assert first_result.total_count == 900
        assert _count(db, KnowledgeBase) == 900

        first_item = db.scalar(
            select(KnowledgeBase).where(
                KnowledgeBase.title == CAMPUS_KNOWLEDGE_ITEMS[0]["title"],
                KnowledgeBase.category == CAMPUS_KNOWLEDGE_ITEMS[0]["category"],
            )
        )
        assert first_item is not None
        first_item.content = "旧内容"
        first_item.source = "旧来源"
        db.commit()

        second_result = asyncio.run(load_complete_rag_data(db, embedding_client, reset_knowledge=False))

        assert second_result.created_count == 0
        assert second_result.updated_count == 900
        assert second_result.total_count == 900
        assert _count(db, KnowledgeBase) == 900

        db.refresh(first_item)
        assert first_item.content == CAMPUS_KNOWLEDGE_ITEMS[0]["content"]
        assert first_item.source == CAMPUS_KNOWLEDGE_ITEMS[0]["source"]
    finally:
        db.close()


def test_complete_rag_loader_reset_only_clears_knowledge_base(tmp_path):
    from app.scripts.load_complete_rag_data import load_complete_rag_data

    db, _ = _build_test_db(tmp_path)
    embedding_client = CountingEmbeddingClient()
    try:
        db.add(User(username="demo", hashed_password="hash", nickname="Demo"))
        db.add(ConversationSession(title="旧会话", summary="保留", round_count=1))
        db.add(QARecord(question="旧问题", answer="旧回答", retrieved_context=[], model_provider="mock"))
        db.add(
            KnowledgeBase(
                title="旧知识",
                category="教务服务",
                content="旧知识内容",
                source="旧数据",
                embedding=[0.0] * 4096,
            )
        )
        db.commit()

        result = asyncio.run(load_complete_rag_data(db, embedding_client, reset_knowledge=True))

        assert result.created_count == 900
        assert result.updated_count == 0
        assert result.total_count == 900
        assert _count(db, KnowledgeBase) == 900
        assert _count(db, User) == 1
        assert _count(db, ConversationSession) == 1
        assert _count(db, QARecord) == 1
    finally:
        db.close()
