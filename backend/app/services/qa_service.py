from typing import Dict, List, Optional

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.conversation_session import ConversationSession
from app.models.qa_record import QARecord


def build_session_title(question: str) -> str:
    normalized = " ".join(question.split())
    return normalized[:30] or "新会话"


def create_conversation_session(db: Session, question: str = "") -> ConversationSession:
    session = ConversationSession(title=build_session_title(question))
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_conversation_session(db: Session, session_id: int) -> Optional[ConversationSession]:
    statement = select(ConversationSession).where(ConversationSession.id == session_id)
    return db.scalars(statement).first()


def get_or_create_conversation_session(db: Session, session_id: Optional[int], question: str) -> ConversationSession:
    if session_id is not None:
        session = get_conversation_session(db, session_id)
        if session is not None:
            return session
    return create_conversation_session(db, question)


def create_qa_record(
    db: Session,
    question: str,
    answer: str,
    retrieved_context: List[Dict],
    model_provider: str,
    session_id: Optional[int] = None,
) -> QARecord:
    record = QARecord(
        session_id=session_id,
        question=question,
        answer=answer,
        retrieved_context=retrieved_context,
        model_provider=model_provider,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def list_recent_session_records(db: Session, session_id: int, limit: int = 3) -> List[QARecord]:
    statement = (
        select(QARecord)
        .where(QARecord.session_id == session_id, QARecord.status == "active")
        .order_by(QARecord.created_at.desc(), QARecord.id.desc())
        .limit(limit)
    )
    return list(reversed(db.scalars(statement).all()))


def update_conversation_session_summary(
    db: Session,
    session: ConversationSession,
    summary: str,
) -> ConversationSession:
    session.summary = summary
    session.round_count = (session.round_count or 0) + 1
    db.commit()
    db.refresh(session)
    return session


def get_qa_record(db: Session, record_id: int) -> Optional[QARecord]:
    statement = select(QARecord).where(QARecord.id == record_id)
    return db.scalars(statement).first()


def list_qa_records(
    db: Session,
    status: str = "active",
    skip: int = 0,
    limit: int = 50
) -> List[QARecord]:
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
