import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.qa_record import QARecord
from app.services.qa_service import (
    create_qa_record,
    list_qa_records,
    get_qa_record,
    count_qa_records,
    archive_qa_record,
    restore_qa_record,
    delete_qa_record,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


def test_create_qa_record(db_session):
    record = create_qa_record(
        db=db_session,
        question="test question",
        answer="test answer",
        retrieved_context=[],
        model_provider="deepseek",
    )
    assert record.id is not None
    assert record.question == "test question"
    assert record.status == "active"


def test_list_qa_records_active_only(db_session):
    # 创建活跃记录
    create_qa_record(db_session, "q1", "a1", [], "deepseek")
    create_qa_record(db_session, "q2", "a2", [], "deepseek")

    # 创建归档记录
    record3 = create_qa_record(db_session, "q3", "a3", [], "deepseek")
    archive_qa_record(db_session, record3.id)

    # 查询活跃记录
    records = list_qa_records(db_session, status="active")
    assert len(records) == 2

    # 查询归档记录
    archived = list_qa_records(db_session, status="archived")
    assert len(archived) == 1


def test_archive_qa_record(db_session):
    record = create_qa_record(db_session, "q1", "a1", [], "deepseek")
    assert record.status == "active"

    archived = archive_qa_record(db_session, record.id)
    assert archived.status == "archived"


def test_restore_qa_record(db_session):
    record = create_qa_record(db_session, "q1", "a1", [], "deepseek")
    archive_qa_record(db_session, record.id)

    restored = restore_qa_record(db_session, record.id)
    assert restored.status == "active"


def test_delete_qa_record(db_session):
    record = create_qa_record(db_session, "q1", "a1", [], "deepseek")
    record_id = record.id

    delete_qa_record(db_session, record_id)

    deleted_record = get_qa_record(db_session, record_id)
    assert deleted_record is None


def test_get_qa_record(db_session):
    record = create_qa_record(db_session, "q1", "a1", [], "deepseek")
    fetched = get_qa_record(db_session, record.id)
    assert fetched.id == record.id
    assert fetched.question == "q1"


def test_count_qa_records(db_session):
    create_qa_record(db_session, "q1", "a1", [], "deepseek")
    create_qa_record(db_session, "q2", "a2", [], "deepseek")
    record3 = create_qa_record(db_session, "q3", "a3", [], "deepseek")
    archive_qa_record(db_session, record3.id)
    assert count_qa_records(db_session, status="active") == 2
    assert count_qa_records(db_session, status="archived") == 1


def test_get_qa_record_not_found(db_session):
    result = get_qa_record(db_session, 999)
    assert result is None


def test_archive_qa_record_not_found(db_session):
    result = archive_qa_record(db_session, 999)
    assert result is None


def test_restore_qa_record_not_found(db_session):
    result = restore_qa_record(db_session, 999)
    assert result is None


def test_delete_qa_record_not_found(db_session):
    result = delete_qa_record(db_session, 999)
    assert result is False
