from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.schemas.qa import AskRequest, AskResponse, QARecordResponse
from app.services.embedding.factory import get_embedding_client
from app.services.llm.factory import get_llm_client
from app.services.qa_service import list_qa_records
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
    return await service.ask(payload.question)


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


@router.get("/records", response_model=list[QARecordResponse])
def records(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    return list_qa_records(db, skip=skip, limit=limit)
