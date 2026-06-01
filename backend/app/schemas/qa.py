from datetime import datetime
from typing import Dict, List

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.knowledge import RetrievedKnowledge


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1)


class AskResponse(BaseModel):
    answer: str
    qa_record_id: int
    retrieved_context: List[RetrievedKnowledge]
    model_provider: str


class QARecordResponse(BaseModel):
    id: int
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

