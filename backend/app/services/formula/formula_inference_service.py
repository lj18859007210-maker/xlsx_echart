"""Day 13 formula inference orchestration service."""

from __future__ import annotations

import logging

from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.db.models.formula_rule_record import FormulaRuleRecordModel
from app.db.models.sheet_record import SheetRecordModel
from app.db.models.task_record import TaskRecordModel

from ..grid_builder import build_sheet_payload
from . import llm_formula_client
from .formula_candidate_schema import FormulaCandidateResponse
from .formula_exceptions import FormulaError
from .formula_parser import FormulaParser
from .formula_sample_verifier import verify_formula_candidate
from .formula_validator import FormulaValidator
from .prompt_builder import PROMPT_VERSION, build_formula_inference_prompt

logger = logging.getLogger(__name__)


def infer_task_formulas(
    task_id: int,
    db: Session,
    model_name: str | None = None,
    max_candidates_per_sheet: int = 5,
) -> dict[str, object]:
    resolved_model = model_name or settings.formula_llm_model
    task = db.scalar(
        select(TaskRecordModel)
        .where(TaskRecordModel.id == task_id)
        .options(
            selectinload(TaskRecordModel.sheets).selectinload(SheetRecordModel.cells),
        )
    )
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    if task.status != "confirmed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Task must be confirmed before formula inference",
        )

    sheets_payload = [
        build_sheet_payload(sheet)
        for sheet in sorted(task.sheets, key=lambda item: item.sheet_index)
    ]

    prompt = build_formula_inference_prompt(
        task_id=task.id,
        sheets=sheets_payload,
        max_candidates_per_sheet=max_candidates_per_sheet,
    )

    try:
        raw_response = llm_formula_client.run_formula_inference(
            prompt=prompt,
            model_name=resolved_model,
        )
    except Exception:
        logger.exception("LLM formula inference call failed")
        return {
            "task_id": task.id,
            "status": task.status,
            "accepted_rules": [],
            "rejected_count": 0,
        }

    try:
        candidate_response = FormulaCandidateResponse.model_validate(raw_response)
    except ValidationError:
        logger.warning("FormulaCandidateResponse validation failed", exc_info=True)
        return {
            "task_id": task.id,
            "status": task.status,
            "accepted_rules": [],
            "rejected_count": 0,
        }

    sheets_by_id = {int(s["sheet_id"]): s for s in sheets_payload}

    accepted_rules: list[dict[str, object]] = []
    rejected_count = 0

    for sheet_candidate in candidate_response.sheet_candidates:
        sheet_id = sheet_candidate.sheet_id
        sheet_payload = sheets_by_id.get(sheet_id)
        if sheet_payload is None:
            rejected_count += len(sheet_candidate.candidates)
            continue

        available_cols = _collect_column_refs(sheet_payload)
        validator = FormulaValidator(available_columns=available_cols)

        for candidate in sheet_candidate.candidates:
            rule = _parse_candidate(candidate.formula_text)
            if rule is None:
                rejected_count += 1
                continue

            validation_issues = validator.validate(rule)
            if validation_issues:
                rejected_count += 1
                continue

            verification_score = verify_formula_candidate(
                sheet_payload,
                candidate.formula_text,
            )

            if verification_score <= 0.0:
                rejected_count += 1
                continue

            record = FormulaRuleRecordModel(
                task_id=task.id,
                sheet_id=sheet_id,
                formula_text=candidate.formula_text,
                formula_type=rule.formula_type,
                description=rule.description,
                confidence=candidate.confidence,
                rule_type="inferred",
                scope_json=rule.scope,
                prompt_version=PROMPT_VERSION,
                model_name=resolved_model,
                verification_passed=True,
                verification_score=verification_score,
                rejection_reason=None,
                raw_candidate_json=candidate.model_dump(),
            )
            db.add(record)
            db.flush()

            accepted_rules.append(
                {
                    "id": record.id,
                    "sheet_id": record.sheet_id,
                    "formula_text": record.formula_text,
                    "formula_type": record.formula_type,
                    "confidence": record.confidence,
                    "verification_score": record.verification_score,
                }
            )

    db.commit()

    return {
        "task_id": task.id,
        "status": task.status,
        "accepted_rules": accepted_rules,
        "rejected_count": rejected_count,
    }


def _collect_column_refs(sheet_payload: dict[str, object]) -> list[str]:
    refs: list[str] = []
    column_paths = sheet_payload.get("column_paths", [])
    if isinstance(column_paths, list):
        for path in column_paths:
            if isinstance(path, list) and path:
                refs.append(f"col_{path[-1]}")
    aligned_grid = sheet_payload.get("aligned_grid", [])
    if isinstance(aligned_grid, list) and aligned_grid and isinstance(aligned_grid[0], list):
        for value in aligned_grid[0]:
            if value not in (None, ""):
                col_ref = f"col_{value}"
                if col_ref not in refs:
                    refs.append(col_ref)
    return refs


def _parse_candidate(formula_text: str):
    try:
        return FormulaParser().parse(formula_text)
    except FormulaError:
        return None
