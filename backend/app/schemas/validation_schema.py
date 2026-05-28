"""Day 15+16 validation schemas."""

from __future__ import annotations

from pydantic import BaseModel


class ValidationIssue(BaseModel):
    sheet_id: int
    sheet_name: str
    row_index: int
    col_index: int
    expected_value: str
    actual_value: str
    formula_text: str
    severity: str
    issue_type: str


class ValidationResult(BaseModel):
    task_id: int
    status: str
    total_issues: int
    error_count: int
    warning_count: int
    issues: list[ValidationIssue]


class ValidationIssueRecord(BaseModel):
    """Schema for persisted validation issue records."""
    id: int
    task_id: int
    sheet_id: int
    formula_rule_id: int | None = None
    row_index: int
    col_index: int
    expected_value: str
    actual_value: str
    formula_text: str
    severity: str
    issue_type: str


class ValidationIssueListResponse(BaseModel):
    task_id: int
    total: int
    issues: list[ValidationIssueRecord]