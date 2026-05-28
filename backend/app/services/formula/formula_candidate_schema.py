"""Strict schemas for Day 13 LLM formula candidates."""

from pydantic import BaseModel, ConfigDict, Field


class FormulaCandidateItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    formula_text: str
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str


class FormulaCandidateSheet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sheet_id: int
    candidates: list[FormulaCandidateItem]


class FormulaCandidateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sheet_candidates: list[FormulaCandidateSheet]
