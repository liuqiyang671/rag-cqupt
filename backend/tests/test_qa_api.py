import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.models.conversation_session import ConversationSession
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


def test_archive_nonexistent_returns_404():
    response = client.put("/api/qa/records/999/archive")
    assert response.status_code == 404


def test_get_nonexistent_returns_404():
    response = client.get("/api/qa/records/999")
    assert response.status_code == 404


def test_delete_nonexistent_returns_404():
    response = client.delete("/api/qa/records/999")
    assert response.status_code == 404


def test_list_records_with_invalid_status_returns_422():
    response = client.get("/api/qa/records?status=garbage")
    assert response.status_code == 422


def test_list_sessions_groups_multiple_records_in_same_conversation():
    db = TestingSessionLocal()
    session = ConversationSession(title="校园卡咨询", summary="用户咨询校园卡挂失。", round_count=2)
    db.add(session)
    db.commit()
    db.refresh(session)
    create_qa_record(db, "你好", "你好，我是校园问答助手。", [], "system", session_id=session.id)
    create_qa_record(db, "我要问一下校园卡怎么挂失", "可以通过校园卡平台挂失。", [], "local", session_id=session.id)
    session_id = session.id
    db.close()

    response = client.get("/api/qa/sessions")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["sessions"]) == 1
    assert data["sessions"][0]["id"] == session_id
    assert data["sessions"][0]["latest_question"] == "我要问一下校园卡怎么挂失"
    assert data["sessions"][0]["latest_model_provider"] == "local"


def test_get_session_records_returns_all_turns_in_order():
    db = TestingSessionLocal()
    session = ConversationSession(title="校园卡咨询")
    db.add(session)
    db.commit()
    db.refresh(session)
    create_qa_record(db, "第一轮", "第一轮回答", [], "system", session_id=session.id)
    create_qa_record(db, "第二轮", "第二轮回答", [], "local", session_id=session.id)
    session_id = session.id
    db.close()

    response = client.get(f"/api/qa/sessions/{session_id}/records")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert [record["question"] for record in data["records"]] == ["第一轮", "第二轮"]


def test_archive_session_archives_its_records():
    db = TestingSessionLocal()
    session = ConversationSession(title="校园卡咨询")
    db.add(session)
    db.commit()
    db.refresh(session)
    record = create_qa_record(db, "第一轮", "第一轮回答", [], "system", session_id=session.id)
    session_id = session.id
    record_id = record.id
    db.close()

    response = client.put(f"/api/qa/sessions/{session_id}/archive")

    assert response.status_code == 200
    assert response.json()["status"] == "archived"
    db = TestingSessionLocal()
    archived_record = db.get(QARecord, record_id)
    assert archived_record is not None
    assert archived_record.status == "archived"
    db.close()


def test_delete_session_deletes_its_records():
    db = TestingSessionLocal()
    session = ConversationSession(title="校园卡咨询")
    db.add(session)
    db.commit()
    db.refresh(session)
    record = create_qa_record(db, "第一轮", "第一轮回答", [], "system", session_id=session.id)
    session_id = session.id
    record_id = record.id
    db.close()

    response = client.delete(f"/api/qa/sessions/{session_id}")

    assert response.status_code == 204
    db = TestingSessionLocal()
    assert db.get(ConversationSession, session_id) is None
    assert db.get(QARecord, record_id) is None
    db.close()
