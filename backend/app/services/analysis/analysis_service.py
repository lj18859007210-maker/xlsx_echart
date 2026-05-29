"""Day 20 - AI analysis orchestration service."""

from __future__ import annotations

from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models.insight_record import InsightRecordModel
from app.db.models.summary_record import SummaryRecordModel
from app.db.models.task_record import TaskRecordModel
from app.schemas.analysis_schema import AnalysisResult

from .llm_client import call_analysis_llm
from .prompt_builder import build_analysis_prompt

_ANALYZE_ALLOWED_STATUSES = frozenset({
    "validated",
    "formula_gap_acknowledged",
    "analyzed",
    "chart_ready",
})


def analyze_task(
    task_id: int,
    db: Session,
    *,
    model_name: str | None = None,
) -> dict[str, object]:
    """Run AI analysis on a task's summary package."""

    # 1. Load task and validate status
    task = db.scalar(
        select(TaskRecordModel).where(TaskRecordModel.id == task_id),
    )
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    if task.status not in _ANALYZE_ALLOWED_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Task must be validated before AI analysis",
        )

    # 2. Load summary (required)
    summary_record = db.scalar(
        select(SummaryRecordModel)
        .where(SummaryRecordModel.task_id == task_id)
        .order_by(SummaryRecordModel.id.desc())
        .limit(1),
    )
    if summary_record is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No summary found. Run summarize first.",
        )

    # 3. Build context package from summary
    context_package = {
        "task_id": task_id,
        "statistical_summary": summary_record.summary_json.get("statistical_summary", []),
        "validation_issues_summary": summary_record.summary_json.get("validation_issues_summary", {}),
        "anomaly_summary": summary_record.summary_json.get("anomaly_summary", {}),
        "slices": summary_record.slice_json,
        "semantic_schema": summary_record.summary_json.get("semantic_schema", []),
    }

    # 4. Build prompt and call LLM
    system_prompt, user_prompt = build_analysis_prompt(context_package)

    try:
        raw_response = call_analysis_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model_name=model_name,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM analysis failed: {exc}",
        ) from exc

    # 5. Validate LLM output with Pydantic
    analysis = _validate_llm_output(raw_response)

    # 6. Build citations
    citations = _build_citations(analysis.key_findings)

    # 7. Attach human-review disclaimer to critical findings
    _attach_disclaimers(analysis)

    # 8. Persist
    _persist_insight(
        task_id=task_id,
        analysis=analysis,
        citations=citations,
        model_name=model_name or settings.analysis_llm_model,
        prompt_version=settings.analysis_prompt_version,
        db=db,
    )

    # Update task status so chart step can proceed
    task.status = "analyzed"
    db.commit()

    return {
        "task_id": task_id,
        "executive_summary": analysis.executive_summary,
        "key_findings": [f.model_dump() for f in analysis.key_findings],
        "risks": [r.model_dump() for r in analysis.risks],
        "recommendations": [r.model_dump() for r in analysis.recommendations],
        "chart_hints": [c.model_dump() for c in analysis.chart_hints],
        "citations": citations,
        "model_name": model_name or settings.analysis_llm_model,
    }


def get_insight(task_id: int, db: Session) -> dict[str, object] | None:
    """Read the latest persisted analysis insight for a task."""
    record = db.scalar(
        select(InsightRecordModel)
        .where(InsightRecordModel.task_id == task_id)
        .order_by(InsightRecordModel.id.desc())
        .limit(1),
    )
    if record is None:
        return None
    return {
        "task_id": record.task_id,
        "version_no": record.version_no,
        "executive_summary": record.executive_summary,
        "key_findings": record.key_findings_json,
        "risks": record.risks_json,
        "recommendations": record.recommendations_json,
        "chart_hints": record.chart_hints_json,
        "citations": record.citations_json,
        "model_name": record.model_name,
    }


def _validate_llm_output(raw: dict[str, object]) -> AnalysisResult:
    """Validate raw LLM JSON against the AnalysisResult schema.

    Raises HTTPException if validation fails.
    """
    try:
        return AnalysisResult(**raw)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM output failed schema validation: {exc}",
        ) from exc


def _build_citations(
    findings: list,
) -> list[dict[str, object]]:
    """Extract and normalize evidence citations from key findings."""
    citations: list[dict[str, object]] = []
    for i, finding in enumerate(findings):
        evidence_list = getattr(finding, "evidence", None) or []
        for j, ev in enumerate(evidence_list):
            citations.append({
                "finding_index": i,
                "finding_title": getattr(finding, "title", ""),
                "evidence_index": j,
                "sheet": getattr(ev, "sheet", ""),
                "metric": getattr(ev, "metric", ""),
                "row": getattr(ev, "row", 0),
                "col": getattr(ev, "col", 0),
                "value": getattr(ev, "value", ""),
            })
    return citations


def _attach_disclaimers(analysis: AnalysisResult) -> None:
    """Attach human-review disclaimer to critical-severity findings."""
    for finding in analysis.key_findings:
        if finding.severity == "critical":
            if "建议人工复核" not in (finding.description or ""):
                finding.description = (
                    (finding.description or "")
                    + " 【建议人工复核】"
                )


def _persist_insight(
    task_id: int,
    analysis: AnalysisResult,
    citations: list[dict[str, object]],
    model_name: str,
    prompt_version: str,
    db: Session,
) -> None:
    db.execute(
        delete(InsightRecordModel).where(
            InsightRecordModel.task_id == task_id,
        ),
    )
    db.add(
        InsightRecordModel(
            task_id=task_id,
            version_no=1,
            executive_summary=analysis.executive_summary,
            key_findings_json=[f.model_dump() for f in analysis.key_findings],
            risks_json=[r.model_dump() for r in analysis.risks],
            recommendations_json=[r.model_dump() for r in analysis.recommendations],
            citations_json=citations,
            chart_hints_json=[c.model_dump() for c in analysis.chart_hints],
            model_name=model_name,
            prompt_version=prompt_version,
        ),
    )
    db.commit()