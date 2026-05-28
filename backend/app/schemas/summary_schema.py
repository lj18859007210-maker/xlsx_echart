"""Day 19 summarization schemas."""

from __future__ import annotations

from pydantic import BaseModel


class SummaryResponse(BaseModel):
    task_id: int
    statistical_summary: list[dict[str, object]]
    validation_issues_summary: dict[str, object]
    anomaly_summary: dict[str, object]
    slices: list[dict[str, object]]
    semantic_schema: list[dict[str, object]]
    token_estimate: int
    token_budget: int
    trimmed: bool