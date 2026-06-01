from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.feedback import Feedback
from app.models.qa_record import QARecord
from app.schemas.feedback import FeedbackCreate, FeedbackResponse

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
def create_feedback(
    payload: FeedbackCreate,
    db: Session = Depends(get_db),
):
    if db.get(QARecord, payload.qa_record_id) is None:
        raise HTTPException(status_code=404, detail="QA record not found")

    feedback = Feedback(**payload.model_dump())
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback


@router.get("", response_model=list[FeedbackResponse])
def list_feedback(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    statement = select(Feedback).order_by(Feedback.created_at.desc()).offset(skip).limit(limit)
    return list(db.scalars(statement).all())
