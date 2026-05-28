"""Day 20 AI analysis schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    sheet: str = ""
    metric: str = ""
    row: int = 0
    col: int = 0
    value: str = ""
    context: str = ""


class Finding(BaseModel):
    title: str
    description: str
    severity: str = "info"
    needs_human_review: bool = False
    evidence: list[EvidenceItem] = Field(default_factory=list)


class Risk(BaseModel):
    title: str
    description: str
    severity: str = "warning"
    mitigation: str = ""


class Recommendation(BaseModel):
    title: str
    description: str
    priority: str = "medium"
    expected_impact: str = ""


class ChartHint(BaseModel):
    chart_type: str = "bar"
    title: str = ""
    metrics: list[str] = Field(default_factory=list)
    dimension: str = ""
    reason: str = ""


class AnalysisResult(BaseModel):
    executive_summary: str = ""
    key_findings: list[Finding] = Field(default_factory=list)
    risks: list[Risk] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)
    chart_hints: list[ChartHint] = Field(default_factory=list)


class AnalysisResponse(BaseModel):
    model_config = {"protected_namespaces": ()}

    task_id: int
    executive_summary: str
    key_findings: list[dict[str, object]]
    risks: list[dict[str, object]]
    recommendations: list[dict[str, object]]
    chart_hints: list[dict[str, object]]
    citations: list[dict[str, object]]
    model_name: str