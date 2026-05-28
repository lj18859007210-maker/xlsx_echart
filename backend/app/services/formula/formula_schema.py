"""Formula DSL Schema definitions."""

from __future__ import annotations

from pydantic import BaseModel


class FormulaType:
    """String constants for formula types."""

    COLUMN_ARITHMETIC = "column_arithmetic"
    ROW_AGGREGATION = "row_aggregation"
    YOY_CHANGE = "yoy_change"
    MOM_CHANGE = "mom_change"
    SHARE_CALCULATION = "share_calculation"


class FormulaRule(BaseModel):
    """Parsed formula rule structure.

    Fields are grouped by purpose.  Only fields relevant to the active
    ``formula_type`` are populated by the parser; the rest keep their
    defaults.
    """

    # Identity & text --------------------------------------------------------
    formula_id: str = ""
    formula_text: str
    formula_type: str
    description: str = ""

    # Column arithmetic fields -----------------------------------------------
    left: str | None = None
    operator: str | None = None
    right: list[str] | None = None

    # Row aggregation fields -------------------------------------------------
    function: str | None = None
    range_start: str | None = None
    range_end: str | None = None
    step: int = 1

    # YoY / MoM fields ------------------------------------------------------
    new_period: str | None = None
    old_period: str | None = None

    # Share calculation fields -----------------------------------------------
    target_column: str | None = None

    # Metadata ---------------------------------------------------------------
    scope: dict[str, object] = {}
    confidence: float = 1.0
    rule_type: str = "derived"
