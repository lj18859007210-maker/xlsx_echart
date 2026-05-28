"""Day 14 formula rule reader — reads, filters, and summarizes task rules."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.formula_rule_record import FormulaRuleRecordModel
from app.db.models.task_record import TaskRecordModel

from .formula_quality_filter import QualityStatus, filter_formula_rules


def read_task_formula_rules(
    task_id: int,
    db: Session,
    quality_threshold: float | None = None,
) -> dict[str, Any]:
    task = db.scalar(select(TaskRecordModel).where(TaskRecordModel.id == task_id))
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    threshold = quality_threshold if quality_threshold is not None else 0.3

    records = list(
        db.scalars(
            select(FormulaRuleRecordModel).where(
                FormulaRuleRecordModel.task_id == task_id,
            ),
        ),
    )

    raw_rules: list[dict[str, object]] = [
        {
            "id": r.id,
            "sheet_id": r.sheet_id,
            "formula_text": r.formula_text,
            "formula_type": r.formula_type,
            "confidence": r.confidence,
            "verification_score": r.verification_score,
        }
        for r in records
    ]

    passed, filtered, conflicts = filter_formula_rules(raw_rules, quality_threshold=threshold)

    rules: list[dict[str, Any]] = []
    for rule_dict in passed:
        rules.append(
            {
                "id": rule_dict["id"],
                "sheet_id": rule_dict["sheet_id"],
                "formula_text": rule_dict["formula_text"],
                "formula_type": rule_dict["formula_type"],
                "confidence": rule_dict["confidence"],
                "verification_score": rule_dict["verification_score"],
                "quality_status": rule_dict.get("quality_status", QualityStatus.PASSED),
            },
        )
    for rule_dict in conflicts:
        rules.append(
            {
                "id": rule_dict["id"],
                "sheet_id": rule_dict["sheet_id"],
                "formula_text": rule_dict["formula_text"],
                "formula_type": rule_dict["formula_type"],
                "confidence": rule_dict["confidence"],
                "verification_score": rule_dict["verification_score"],
                "quality_status": rule_dict.get("quality_status", QualityStatus.CONFLICT),
            },
        )
    for rule_dict in filtered:
        rules.append(
            {
                "id": rule_dict["id"],
                "sheet_id": rule_dict["sheet_id"],
                "formula_text": rule_dict["formula_text"],
                "formula_type": rule_dict["formula_type"],
                "confidence": rule_dict["confidence"],
                "verification_score": rule_dict["verification_score"],
                "quality_status": rule_dict.get("quality_status", QualityStatus.FILTERED_LOW_SCORE),
            },
        )

    return {
        "task_id": task.id,
        "status": task.status,
        "total_inferred": len(raw_rules),
        "passed": len(passed),
        "filtered": len(filtered),
        "conflict": len(conflicts),
        "has_gap": len(passed) == 0,
        "rules": rules,
    }

