from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class FeedbackCreate(BaseModel):
    qa_record_id: int
    rating: Literal["like", "dislike"]
    comment: str | None = Field(default=None, max_length=1000)


class FeedbackResponse(BaseModel):
    id: int
    qa_record_id: int
    rating: str
    comment: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

