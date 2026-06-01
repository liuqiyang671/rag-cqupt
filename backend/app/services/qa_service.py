from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.qa_record import QARecord


def create_qa_record(
    db: Session,
    question: str,
    answer: str,
    retrieved_context: list[dict],
    model_provider: str,
) -> QARecord:
    record = QARecord(
        question=question,
        answer=answer,
        retrieved_context=retrieved_context,
        model_provider=model_provider,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_qa_record(db: Session, record_id: int) -> Optional[QARecord]:
    statement = select(QARecord).where(QARecord.id == record_id)
    return db.scalars(statement).first()


def list_qa_records(
    db: Session,
    status: str = "active",
    skip: int = 0,
    limit: int = 50
) -> list[QARecord]:
    statement = (
        select(QARecord)
        .where(QARecord.status == status)
        .order_by(QARecord.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(db.scalars(statement).all())


def count_qa_records(db: Session, status: str = "active") -> int:
    statement = select(func.count()).select_from(QARecord).where(QARecord.status == status)
    return db.scalar(statement) or 0


def archive_qa_record(db: Session, record_id: int) -> Optional[QARecord]:
    record = get_qa_record(db, record_id)
    if record:
        record.status = "archived"
        db.commit()
        db.refresh(record)
    return record


def restore_qa_record(db: Session, record_id: int) -> Optional[QARecord]:
    record = get_qa_record(db, record_id)
    if record:
        record.status = "active"
        db.commit()
        db.refresh(record)
    return record


def delete_qa_record(db: Session, record_id: int) -> bool:
    record = get_qa_record(db, record_id)
    if record:
        db.delete(record)
        db.commit()
        return True
    return False
