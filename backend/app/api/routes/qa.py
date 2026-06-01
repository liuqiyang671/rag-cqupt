from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.ai_errors import AIServiceError
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.schemas.qa import AskRequest, AskResponse, QARecordResponse, QARecordListResponse
from app.services.embedding.factory import get_embedding_client
from app.services.llm.factory import get_llm_client
from app.services.qa_service import (
    list_qa_records,
    count_qa_records,
    get_qa_record,
    archive_qa_record,
    restore_qa_record,
    delete_qa_record,
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
        return await service.ask(payload.question)
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
        service.ask_stream(payload.question),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


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
