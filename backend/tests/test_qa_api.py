import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.models.qa_record import QARecord
from app.services.qa_service import create_qa_record


engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(engine)
TestingSessionLocal = sessionmaker(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(engine)
    yield
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(engine)


def test_list_records_with_status_filter():
    db = TestingSessionLocal()
    create_qa_record(db, "q1", "a1", [], "deepseek")
    create_qa_record(db, "q2", "a2", [], "deepseek")
    record3 = create_qa_record(db, "q3", "a3", [], "deepseek")
    db.close()

    # 列出活跃记录
    response = client.get("/api/qa/records?status=active")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["records"]) == 3

    # 归档一条记录
    response = client.put(f"/api/qa/records/{record3.id}/archive")
    assert response.status_code == 200
    assert response.json()["status"] == "archived"

    # 再次列出活跃记录
    response = client.get("/api/qa/records?status=active")
    assert response.json()["total"] == 2

    # 列出归档记录
    response = client.get("/api/qa/records?status=archived")
    assert response.json()["total"] == 1


def test_archive_record():
    db = TestingSessionLocal()
    record = create_qa_record(db, "q1", "a1", [], "deepseek")
    db.close()

    response = client.put(f"/api/qa/records/{record.id}/archive")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "archived"


def test_restore_record():
    db = TestingSessionLocal()
    record = create_qa_record(db, "q1", "a1", [], "deepseek")
    db.close()

    # 先归档
    client.put(f"/api/qa/records/{record.id}/archive")

    # 再恢复
    response = client.put(f"/api/qa/records/{record.id}/restore")
    assert response.status_code == 200
    assert response.json()["status"] == "active"


def test_delete_record():
    db = TestingSessionLocal()
    record = create_qa_record(db, "q1", "a1", [], "deepseek")
    db.close()

    response = client.delete(f"/api/qa/records/{record.id}")
    assert response.status_code == 204

    # 验证已删除
    response = client.get(f"/api/qa/records/{record.id}")
    assert response.status_code == 404


def test_get_single_record():
    db = TestingSessionLocal()
    record = create_qa_record(db, "q1", "a1", [], "deepseek")
    db.close()

    response = client.get(f"/api/qa/records/{record.id}")
    assert response.status_code == 200
    assert response.json()["question"] == "q1"
