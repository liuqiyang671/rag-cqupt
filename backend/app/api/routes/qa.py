from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.ai_errors import AIServiceError
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.schemas.qa import (
    AskRequest,
    AskResponse,
    ConversationSessionListResponse,
    ConversationSessionResponse,
    QARecordResponse,
    QARecordListResponse,
)
from app.services.embedding.factory import get_embedding_client
from app.services.llm.factory import get_llm_client
from app.services.qa_service import (
    list_qa_records,
    count_qa_records,
    get_qa_record,
    archive_qa_record,
    restore_qa_record,
    delete_qa_record,
    archive_conversation_session,
    count_conversation_sessions,
    delete_conversation_session,
    get_conversation_session,
    get_latest_session_record,
    list_conversation_sessions,
    list_session_qa_records,
)
from app.services.rag_service import RAGService

router = APIRouter(prefix="/qa", tags=["qa"])


@router.post("/ask", response_model=AskResponse)
async def ask(
    payload: AskRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    service = RAGService(
        db=db,
        embedding_client=get_embedding_client(settings),
        llm_client=get_llm_client(settings),
        model_provider=settings.model_provider,
        top_k=settings.top_k,
    )
    try:
        return await service.ask(payload.question, session_id=payload.session_id)
    except AIServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/ask/stream")
async def ask_stream(
    payload: AskRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    service = RAGService(
        db=db,
        embedding_client=get_embedding_client(settings),
        llm_client=get_llm_client(settings),
        model_provider=settings.model_provider,
        top_k=settings.top_k,
    )
    return StreamingResponse(
        service.ask_stream(payload.question, session_id=payload.session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


def _build_session_response(db: Session, session) -> ConversationSessionResponse:
    latest_record = get_latest_session_record(db, session.id)
    return ConversationSessionResponse(
        id=session.id,
        title=session.title,
        summary=session.summary,
        round_count=session.round_count,
        status=session.status,
        latest_question=latest_record.question if latest_record else None,
        latest_answer=latest_record.answer if latest_record else None,
        latest_model_provider=latest_record.model_provider if latest_record else None,
        latest_record_id=latest_record.id if latest_record else None,
        latest_record_created_at=latest_record.created_at if latest_record else None,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.get("/sessions", response_model=ConversationSessionListResponse)
def sessions(
    status: Literal["active", "archived"] = "active",
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    session_list = list_conversation_sessions(db, status=status, skip=skip, limit=limit)
    return ConversationSessionListResponse(
        sessions=[_build_session_response(db, session) for session in session_list],
        total=count_conversation_sessions(db, status=status),
        skip=skip,
        limit=limit,
    )


@router.get("/sessions/{session_id}/records", response_model=QARecordListResponse)
def session_records(session_id: int, db: Session = Depends(get_db)):
    session = get_conversation_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    records_list = list_session_qa_records(db, session_id=session_id, status="active")
    return QARecordListResponse(
        records=records_list,
        total=len(records_list),
        skip=0,
        limit=len(records_list),
    )


@router.put("/sessions/{session_id}/archive", response_model=ConversationSessionResponse)
def archive_session(session_id: int, db: Session = Depends(get_db)):
    session = archive_conversation_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return _build_session_response(db, session)


@router.delete("/sessions/{session_id}", status_code=204)
def delete_session(session_id: int, db: Session = Depends(get_db)):
    success = delete_conversation_session(db, session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return None


@router.get("/records", response_model=QARecordListResponse)
def records(
    status: Literal["active", "archived"] = "active",
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    records_list = list_qa_records(db, status=status, skip=skip, limit=limit)
    total = count_qa_records(db, status=status)
    return QARecordListResponse(
        records=records_list,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/records/{record_id}", response_model=QARecordResponse)
def get_record(record_id: int, db: Session = Depends(get_db)):
    record = get_qa_record(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    return record


@router.put("/records/{record_id}/archive", response_model=QARecordResponse)
def archive_record(record_id: int, db: Session = Depends(get_db)):
    record = archive_qa_record(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    return record


@router.put("/records/{record_id}/restore", response_model=QARecordResponse)
def restore_record(record_id: int, db: Session = Depends(get_db)):
    record = restore_qa_record(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    return record


@router.delete("/records/{record_id}", status_code=204)
def delete_record(record_id: int, db: Session = Depends(get_db)):
    success = delete_qa_record(db, record_id)
    if not success:
        raise HTTPException(status_code=404, detail="Record not found")
    return None
