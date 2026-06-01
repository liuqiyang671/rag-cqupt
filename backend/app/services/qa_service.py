from sqlalchemy import select
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


def list_qa_records(db: Session, skip: int = 0, limit: int = 50) -> list[QARecord]:
    statement = select(QARecord).order_by(QARecord.created_at.desc()).offset(skip).limit(limit)
    return list(db.scalars(statement).all())

