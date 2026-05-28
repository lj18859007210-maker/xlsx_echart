from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.review_schema import (
    ConfirmStructureVersionRequest,
    ConfirmStructureVersionResponse,
    SaveStructureVersionRequest,
    StructureVersionSaveResponse,
    TaskReviewResponse,
)
from app.schemas.task_schema import (
    TaskInferFormulaRequest,
    TaskInferFormulaResponse,
    TaskParseResponse,
)
from app.services.excel_parse_service import parse_task_workbook
from app.services.formula import formula_inference_service
from app.services.review_service import (
    build_task_review,
    confirm_structure_version,
    save_structure_version,
)

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


@router.post(
    "/{task_id}/structure-versions",
    response_model=StructureVersionSaveResponse,
    status_code=201,
)
def create_structure_version(
    task_id: int,
    request: SaveStructureVersionRequest,
    db: Session = Depends(get_db),
) -> StructureVersionSaveResponse:
    payload = save_structure_version(
        task_id,
        request.base_structure_version,
        [sheet.model_dump() for sheet in request.sheets],
        db,
    )
    return StructureVersionSaveResponse(**payload)


@router.post("/{task_id}/confirm", response_model=ConfirmStructureVersionResponse)
def confirm_task_structure(
    task_id: int,
    request: ConfirmStructureVersionRequest,
    db: Session = Depends(get_db),
) -> ConfirmStructureVersionResponse:
    payload = confirm_structure_version(task_id, request.structure_version, db)
    return ConfirmStructureVersionResponse(**payload)


@router.post("/{task_id}/infer-formulas", response_model=TaskInferFormulaResponse)
def infer_task_formulas(
    task_id: int,
    request: TaskInferFormulaRequest = Body(TaskInferFormulaRequest()),
    db: Session = Depends(get_db),
) -> TaskInferFormulaResponse:
    payload = formula_inference_service.infer_task_formulas(
        task_id,
        db,
        model_name=request.model_name,
        max_candidates_per_sheet=request.max_candidates_per_sheet,
    )
    return TaskInferFormulaResponse(**payload)
