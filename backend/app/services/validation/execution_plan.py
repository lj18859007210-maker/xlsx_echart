"""Day 15 execution plan builder — DSL formulas → column-indexed execution plans."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.formula.formula_parser import FormulaParser
from app.services.formula.formula_schema import FormulaType


class PlanKind:
    ROW_WISE = "row_wise"
    AGGREGATE = "aggregate"


@dataclass
class ExecutionPlan:
    kind: str
    target_column_index: int
    formula_text: str
    rule_id: int | None = None
    operator: str | None = None
    operand_indices: list[int] = field(default_factory=list)
    aggregate_func: str | None = None
    row_start: int | None = None
    row_end: int | None = None
    step: int = 1


def build_execution_plan(
    rule: dict[str, object],
    column_map: dict[str, int],
) -> ExecutionPlan | None:
    """Convert a single formula rule into an execution plan.

    Returns None for unsupported formula types (yoy, mom, share) or
    when column references cannot be resolved.
    """
    formula_text = str(rule["formula_text"])
    formula_type = str(rule.get("formula_type", ""))
    rule_id_raw = rule.get("id")
    rule_id = int(rule_id_raw) if rule_id_raw is not None else None

    if formula_type == FormulaType.COLUMN_ARITHMETIC:
        plan = _build_column_arithmetic_plan(formula_text, column_map)
    elif formula_type == FormulaType.ROW_AGGREGATION:
        plan = _build_row_aggregation_plan(formula_text, column_map)
    else:
        plan = None

    if plan is not None:
        plan.rule_id = rule_id

    return plan


def build_execution_plans(
    rules: list[dict[str, object]],
    column_map: dict[str, int],
) -> list[ExecutionPlan]:
    """Convert a list of formula rules into execution plans, skipping unsupported ones."""
    plans: list[ExecutionPlan] = []
    for rule in rules:
        plan = build_execution_plan(rule, column_map)
        if plan is not None:
            plans.append(plan)
    return plans


def _build_column_arithmetic_plan(
    formula_text: str,
    column_map: dict[str, int],
) -> ExecutionPlan | None:
    parsed = FormulaParser().parse(formula_text)
    if (
        not parsed.left
        or not parsed.operator
        or not parsed.right
        or len(parsed.right) != 2
    ):
        return None

    target_idx = column_map.get(parsed.left)
    left_idx = column_map.get(parsed.right[0])
    right_idx = column_map.get(parsed.right[1])

    if target_idx is None or left_idx is None or right_idx is None:
        return None

    return ExecutionPlan(
        kind=PlanKind.ROW_WISE,
        target_column_index=target_idx,
        operator=parsed.operator,
        operand_indices=[left_idx, right_idx],
        formula_text=formula_text,
    )


def _build_row_aggregation_plan(
    formula_text: str,
    column_map: dict[str, int],
) -> ExecutionPlan | None:
    parsed = FormulaParser().parse(formula_text)
    if not parsed.function or not parsed.range_start:
        return None

    # Row aggregation target: "row_Total" → "Total" for column_map lookup
    target_name = _strip_row_prefix(parsed.left)
    target_idx = column_map.get(target_name)
    if target_idx is None:
        # Also try with "row_" prefix as fallback
        target_idx = column_map.get(parsed.left) if parsed.left else None
    if target_idx is None:
        return None

    row_start = _extract_row_index(parsed.range_start)
    row_end = _extract_row_index(parsed.range_end) if parsed.range_end else None

    return ExecutionPlan(
        kind=PlanKind.AGGREGATE,
        target_column_index=target_idx,
        aggregate_func=parsed.function,
        row_start=row_start,
        row_end=row_end,
        step=parsed.step,
        formula_text=formula_text,
    )


def _strip_row_prefix(name: str | None) -> str:
    """Strip 'row_' prefix from a name like 'row_Total' → 'Total'."""
    if not name:
        return ""
    if name.startswith("row_"):
        return name[4:]
    return name


def _extract_row_index(row_ref: str) -> int | None:
    """Extract numeric row index from a row reference like 'row_3'.

    Returns the 1-based row index, or None if unparseable.
    """
    if not row_ref:
        return None
    suffix = row_ref.split("_", 1)[-1] if "_" in row_ref else row_ref
    try:
        return int(suffix)
    except ValueError:
        return None