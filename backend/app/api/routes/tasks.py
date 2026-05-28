from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.review_schema import TaskReviewResponse
from app.schemas.task_schema import TaskParseResponse
from app.services.excel_parse_service import parse_task_workbook
from app.services.review_service import build_task_review

router = APIRouter()


@router.get("/ping")
def tasks_ping() -> dict[str, str]:
    return {"module": "tasks", "status": "ready"}


@router.post("/{task_id}/parse", response_model=TaskParseResponse)
def parse_task(task_id: int, db: Session = Depends(get_db)) -> TaskParseResponse:
    payload = parse_task_workbook(db, task_id)
    return TaskParseResponse(**payload)


@router.get("/{task_id}/review", response_model=TaskReviewResponse)
def get_task_review(task_id: int, db: Session = Depends(get_db)) -> TaskReviewResponse:
    payload = build_task_review(task_id, db)
    return TaskReviewResponse(**payload)
