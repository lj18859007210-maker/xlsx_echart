"""Day 19 - statistical summary builder."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation


def build_statistical_summary(
    aligned_grid: list[list],
    column_kinds: list[str],
    column_paths: list,
    sheet_name: str = "",
) -> dict[str, object]:
    """Build per-column statistical summary for a single sheet."""
    columns: list[dict[str, object]] = []

    for col_idx, kind in enumerate(column_kinds):
        name = _column_name(column_paths, col_idx)
        values = _collect_values(aligned_grid, col_idx)
        missing = _missing_rate(aligned_grid, col_idx)

        col_summary: dict[str, object] = {
            "name": name,
            "kind": kind,
            "count": len(values),
            "missing_rate": missing,
        }

        if values and kind == "measure":
            sorted_vals = sorted(values)
            n = len(sorted_vals)
            mean_val = sum(values) / n
            col_summary.update({
                "mean": float(mean_val),
                "median": float(_median(sorted_vals, n)),
                "min": float(min(values)),
                "max": float(max(values)),
                "volatility": _volatility(values, float(mean_val), n),
                "trend": _trend(values),
            })

        columns.append(col_summary)

    return {
        "sheet_name": sheet_name,
        "columns": columns,
    }


def _collect_values(grid: list[list], col_idx: int) -> list[Decimal]:
    values: list[Decimal] = []
    for row_idx in range(1, len(grid)):
        val = _to_decimal_safe(grid[row_idx][col_idx])
        if val is not None:
            values.append(val)
    return values


def _missing_rate(grid: list[list], col_idx: int) -> float:
    total = len(grid) - 1
    if total <= 0:
        return 0.0
    missing = sum(
        1 for r in range(1, len(grid))
        if _to_decimal_safe(grid[r][col_idx]) is None
    )
    return round(missing / total, 4)


def _median(sorted_vals: list[Decimal], n: int) -> Decimal:
    if n % 2 == 1:
        return sorted_vals[n // 2]
    mid = n // 2
    return (sorted_vals[mid - 1] + sorted_vals[mid]) / Decimal("2")


def _volatility(values: list[Decimal], mean: float, n: int) -> float:
    """Coefficient of variation = std / |mean|."""
    if n < 2 or mean == 0:
        return 0.0
    variance = sum((float(v) - mean) ** 2 for v in values) / n
    return round(variance ** 0.5 / abs(mean), 4)


def _trend(values: list[Decimal]) -> str:
    if len(values) < 2:
        return "flat"
    if values[-1] > values[0]:
        return "up"
    if values[-1] < values[0]:
        return "down"
    return "flat"


def _to_decimal_safe(value: object) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value).replace(",", ""))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _column_name(column_paths: list, col_idx: int) -> str:
    if col_idx < len(column_paths) and isinstance(column_paths[col_idx], list):
        return str(column_paths[col_idx][-1]) if column_paths[col_idx] else f"col_{col_idx}"
    return f"col_{col_idx}"