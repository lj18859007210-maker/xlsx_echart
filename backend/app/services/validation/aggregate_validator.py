"""Day 15 aggregate validator — validates SUM/AVG/COUNT formulas."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from .execution_plan import ExecutionPlan, PlanKind


def validate_aggregates(
    aligned_grid: list[list],
    plans: list[ExecutionPlan],
) -> list[dict[str, object]]:
    """Validate aggregate formulas against the aligned grid.

    The target value is expected at the row immediately following the range
    (e.g., Total row after subtotal rows).
    """
    agg_plans = [p for p in plans if p.kind == PlanKind.AGGREGATE]
    if not agg_plans or len(aligned_grid) < 2:
        return []

    issues: list[dict[str, object]] = []

    for plan in agg_plans:
        target_idx = plan.target_column_index
        start = max(plan.row_start or 1, 1)
        end = plan.row_end if plan.row_end is not None else len(aligned_grid) - 2
        step = plan.step or 1

        # Target row is right after the range
        target_row = end + 1
        try:
            target_val = _to_decimal(aligned_grid[target_row][target_idx])
        except (IndexError, InvalidOperation, TypeError):
            continue

        values: list[Decimal] = []
        for row_index in range(start, end + 1, step):
            try:
                values.append(_to_decimal(aligned_grid[row_index][target_idx]))
            except (IndexError, InvalidOperation, TypeError):
                continue

        if not values:
            continue

        expected = _compute_aggregate(values, plan.aggregate_func or "")
        if expected is None:
            continue

        if expected != target_val:
            issues.append(
                {
                    "row_index": target_row,
                    "col_index": target_idx,
                    "expected_value": str(expected),
                    "actual_value": str(target_val),
                    "formula_text": plan.formula_text,
                    "severity": "error",
                    "issue_type": "aggregate_mismatch",
                    "rule_id": plan.rule_id,
                },
            )

    return issues


def _to_decimal(value: object) -> Decimal:
    if value in (None, ""):
        raise InvalidOperation
    return Decimal(str(value).replace(",", ""))


def _compute_aggregate(values: list[Decimal], func: str) -> Decimal | None:
    if not values:
        return None
    if func == "sum":
        return sum(values, Decimal("0"))
    if func == "avg":
        return sum(values, Decimal("0")) / len(values)
    if func == "count":
        return Decimal(len(values))
    return None