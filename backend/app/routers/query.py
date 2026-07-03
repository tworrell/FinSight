from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.query.agent import answer_question
from app.schemas import QueryRequest, QueryResponse

router = APIRouter(tags=["query"])


@router.post("/query", response_model=QueryResponse)
def query(payload: QueryRequest, db: Session = Depends(get_db)):
    return answer_question(db, payload.question)
