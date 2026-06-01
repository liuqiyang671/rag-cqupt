from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.knowledge import RetrievedKnowledge


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1)


class AskResponse(BaseModel):
    answer: str
    qa_record_id: int
    retrieved_context: list[RetrievedKnowledge]
    model_provider: str


class QARecordResponse(BaseModel):
    id: int
    question: str
    answer: str
    retrieved_context: list[dict]
    model_provider: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

