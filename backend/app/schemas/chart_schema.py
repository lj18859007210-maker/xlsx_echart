"""Day 21 chart recommendation schema."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChartSpecItem(BaseModel):
    chart_type: str = ""
    title: str = ""
    x_field: str = ""
    y_fields: list[str] = Field(default_factory=list)
    series: list[dict[str, object]] = Field(default_factory=list)
    highlights: list[dict[str, object]] = Field(default_factory=list)
    source_cells: list[str] = Field(default_factory=list)
    filter_conditions: str = ""
    reason: str = ""


class ChartRecommendResponse(BaseModel):
    task_id: int
    total: int
    charts: list[dict[str, object]]
    no_chart_reasons: list[str] = Field(default_factory=list)


class ChartSpecListResponse(BaseModel):
    task_id: int
    total: int
    charts: list[dict[str, object]]