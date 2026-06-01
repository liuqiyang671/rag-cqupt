from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.knowledge import RetrievedKnowledge


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1)
    session_id: Optional[int] = None


class AskResponse(BaseModel):
    answer: str
    qa_record_id: int
    retrieved_context: List[RetrievedKnowledge]
    model_provider: str
    session_id: int
    conversation_summary: str


class QARecordResponse(BaseModel):
    id: int
    session_id: Optional[int] = None
    question: str
    answer: str
    retrieved_context: List[Dict]
    model_provider: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QARecordListResponse(BaseModel):
    records: List[QARecordResponse]
    total: int
    skip: int
    limit: int


class ConversationSessionResponse(BaseModel):
    id: int
    title: str
    summary: str
    round_count: int
    status: str
    latest_question: Optional[str] = None
    latest_answer: Optional[str] = None
    latest_model_provider: Optional[str] = None
    latest_record_id: Optional[int] = None
    latest_record_created_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationSessionListResponse(BaseModel):
    sessions: List[ConversationSessionResponse]
    total: int
    skip: int
    limit: int
