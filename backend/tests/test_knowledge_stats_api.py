from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.main import app
from app.models import Feedback, KnowledgeBase, QARecord, User  # noqa: F401


def test_knowledge_stats_returns_full_category_counts_outside_pagination(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        db.add_all(
            [
                KnowledgeBase(
                    title=f"教务内置知识 {index}",
                    category="教务服务",
                    content="教务内置知识内容",
                    source="教务处服务指南",
                    embedding=[0.0] * 4096,
                )
                for index in range(120)
            ]
        )
        db.add_all(
            [
                KnowledgeBase(
                    title=f"图书馆文档切片 {index}",
                    category="图书馆服务",
                    content="图书馆文档切片内容",
                    source="上传文档: library.md",
                    document_name="library.md",
                    chunk_index=index + 1,
                    chunk_total=3,
                    chunking_method="markdown_heading",
                    embedding=[0.0] * 4096,
                )
                for index in range(3)
            ]
        )
        db.add(
            KnowledgeBase(
                title="图书馆另一个文档切片",
                category="图书馆服务",
                content="图书馆另一个文档切片内容",
                source="上传文档: seats.md",
                document_name="seats.md",
                chunk_index=1,
                chunk_total=1,
                chunking_method="full_document",
                embedding=[0.0] * 4096,
            )
        )
        db.commit()
    finally:
        db.close()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    response = client.get("/api/knowledge/stats")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_items"] == 124

    stats = {item["category"]: item for item in payload["categories"]}
    assert stats["教务服务"]["item_count"] == 120
    assert stats["教务服务"]["document_count"] == 0
    assert stats["教务服务"]["chunk_count"] == 0

    assert stats["图书馆服务"]["item_count"] == 4
    assert stats["图书馆服务"]["document_count"] == 2
    assert stats["图书馆服务"]["chunk_count"] == 4
    assert stats["校园卡服务"]["item_count"] == 0
