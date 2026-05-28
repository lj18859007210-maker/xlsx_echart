"""Day 15 row-wise validator — evaluates column arithmetic formulas row by row."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from .execution_plan import ExecutionPlan, PlanKind


def validate_rows(
    aligned_grid: list[list],
    plans: list[ExecutionPlan],
) -> list[dict[str, object]]:
    """Validate row-wise formulas against the aligned grid.

    Returns a list of validation issues with coordinates and rule_id.
    """
    row_plans = [p for p in plans if p.kind == PlanKind.ROW_WISE]
    if not row_plans or len(aligned_grid) < 2:
        return []

    issues: list[dict[str, object]] = []

    for plan in row_plans:
        target_idx = plan.target_column_index
        left_idx = plan.operand_indices[0]
        right_idx = plan.operand_indices[1]
        op = plan.operator

        for row_index, row in enumerate(aligned_grid):
            if row_index == 0:
                continue  # skip header row

            if not isinstance(row, list):
                continue

            try:
                left_val = _to_decimal(row[left_idx])
                right_val = _to_decimal(row[right_idx])
                target_val = _to_decimal(row[target_idx])
            except (IndexError, InvalidOperation, TypeError):
                continue  # skip non-numeric / out of bounds

            if op == "/" and right_val == 0:
                issues.append(
                    {
                        "row_index": row_index,
                        "col_index": target_idx,
                        "expected_value": "",
                        "actual_value": str(target_val),
                        "formula_text": plan.formula_text,
                        "severity": "warning",
                        "issue_type": "division_by_zero",
                        "rule_id": plan.rule_id,
                    },
                )
                continue

            expected = _apply_operator(left_val, right_val, op)
            if expected is None:
                continue

            if expected != target_val:
                issues.append(
                    {
                        "row_index": row_index,
                        "col_index": target_idx,
                        "expected_value": str(expected),
                        "actual_value": str(target_val),
                        "formula_text": plan.formula_text,
                        "severity": "error",
                        "issue_type": "mismatch",
                        "rule_id": plan.rule_id,
                    },
                )

    return issues


def _to_decimal(value: object) -> Decimal:
    if value in (None, ""):
        raise InvalidOperation
    return Decimal(str(value).replace(",", ""))


def _apply_operator(left: Decimal, right: Decimal, op: str) -> Decimal | None:
    if op == "+":
        return left + right
    if op == "-":
        return left - right
    if op == "*":
        return left * right
    if op == "/" and right != 0:
        return left / right
    return None