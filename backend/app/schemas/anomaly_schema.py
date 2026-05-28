"""Day 17 anomaly detection schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AnomalyIssue(BaseModel):
    row_index: int
    col_index: int
    cell_address: str = ""
    issue_type: str
    severity: str
    metric_name: str
    detection_source: str
    reason: str
    score: float


class AnomalyDetectionResult(BaseModel):
    task_id: int
    status: str
    detection_mode: str
    anomaly_issue_count: int
    rule_hits: int = 0
    stat_hits: int = 0
    issues: list[AnomalyIssue]


class AnomalyIssueRecord(BaseModel):
    """Schema for persisted anomaly issue records."""
    id: int
    task_id: int
    sheet_id: int
    row_index: int
    col_index: int
    cell_address: str = ""
    issue_type: str
    severity: str
    metric_name: str
    detection_source: str
    reason: str
    score: float


class AnomalyIssueListResponse(BaseModel):
    task_id: int
    total: int
    issues: list[AnomalyIssueRecord]