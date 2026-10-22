from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import require_assigned_position
from app.db.session import get_db
from app.models.staff import Staff
from app.schemas.chat import ChatAsk, ChatResponse
from app.agents.position_qa import ask_position_question

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/ask", response_model=ChatResponse)
def ask(payload: ChatAsk, current: Staff = Depends(require_assigned_position), db: Session = Depends(get_db)):
    return ask_position_question(db, current.position.code, payload.question)
