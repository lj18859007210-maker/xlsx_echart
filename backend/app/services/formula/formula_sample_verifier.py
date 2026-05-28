"""Sample-data verification for Day 13 formula candidates."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from .formula_exceptions import FormulaError
from .formula_parser import FormulaParser
from .formula_schema import FormulaType
from .formula_validator import FormulaValidator


def verify_formula_candidate(sheet_payload: dict[str, object], formula_text: str) -> float:
    """Score a candidate formula against aligned sample rows.

    Day 13 only accepts directly verifiable formulas. Unsupported formula
    shapes return 0.0 so they can be rejected conservatively.
    """
    try:
        rule = FormulaParser().parse(formula_text)
    except FormulaError:
        return 0.0

    available_columns = _available_column_refs(sheet_payload)
    validator = FormulaValidator(available_columns=available_columns, available_rows=[])
    if [issue for issue in validator.validate(rule) if not issue.startswith("Division by column")]:
        return 0.0

    if (
        rule.formula_type != FormulaType.COLUMN_ARITHMETIC
        or not rule.left
        or not rule.right
        or len(rule.right) != 2
        or not rule.operator
    ):
        return 0.0

    aligned_grid = sheet_payload.get("aligned_grid")
    if not isinstance(aligned_grid, list) or len(aligned_grid) < 2:
        return 0.0

    column_map = _build_column_map(sheet_payload, aligned_grid)
    target_index = column_map.get(rule.left)
    left_index = column_map.get(rule.right[0])
    right_index = column_map.get(rule.right[1])
    if target_index is None or left_index is None or right_index is None:
        return 0.0

    total = 0
    matched = 0
    for row in aligned_grid[1:]:
        if not isinstance(row, list):
            continue
        try:
            left_value = _to_decimal(row[left_index])
            right_value = _to_decimal(row[right_index])
            target_value = _to_decimal(row[target_index])
        except (IndexError, InvalidOperation, TypeError):
            continue

        expected = _apply_operator(left_value, right_value, rule.operator)
        if expected is None:
            continue

        total += 1
        if expected == target_value:
            matched += 1

    return 0.0 if total == 0 else matched / total


def _available_column_refs(sheet_payload: dict[str, object]) -> list[str]:
    return list(_build_column_map(sheet_payload, sheet_payload.get("aligned_grid", [])).keys())


def _build_column_map(
    sheet_payload: dict[str, object],
    aligned_grid: object,
) -> dict[str, int]:
    column_map: dict[str, int] = {}
    column_paths = sheet_payload.get("column_paths", [])
    if isinstance(column_paths, list):
        for index, path in enumerate(column_paths):
            if isinstance(path, list) and path:
                column_map[f"col_{path[-1]}"] = index

    if isinstance(aligned_grid, list) and aligned_grid and isinstance(aligned_grid[0], list):
        for index, value in enumerate(aligned_grid[0]):
            if value not in (None, ""):
                column_map.setdefault(f"col_{value}", index)

    return column_map


def _to_decimal(value: object) -> Decimal:
    if value in (None, ""):
        raise InvalidOperation
    return Decimal(str(value).replace(",", ""))


def _apply_operator(left_value: Decimal, right_value: Decimal, operator: str) -> Decimal | None:
    if operator == "+":
        return left_value + right_value
    if operator == "-":
        return left_value - right_value
    if operator == "*":
        return left_value * right_value
    if operator == "/" and right_value != 0:
        return left_value / right_value
    return None
