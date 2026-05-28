"""Day 21 ChartSpec builder — transforms rules + data into ECharts-compatible specs."""

from __future__ import annotations


def _col_letter(idx: int) -> str:
    """Convert 0-based column index to Excel column letter."""
    result = ""
    n = idx
    while n >= 0:
        result = chr(65 + (n % 26)) + result
        n = n // 26 - 1
    return result


def _cell_range(
    start_row: int, start_col: int, end_row: int, end_col: int,
) -> str:
    """Return Excel-style cell range, e.g. B2:D5 (rows 0-based, cols 0-based)."""
    return f"{_col_letter(start_col)}{start_row + 1}:{_col_letter(end_col)}{end_row + 1}"


def _safe_float(val: object) -> float | None:
    """Convert to float or return None."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        try:
            return float(val.strip())
        except (ValueError, TypeError):
            return None
    return None


def build_chart_spec(
    chart_rule: dict[str, object],
    aligned_grid: list[list[object]],
    column_kinds: list[str],
    column_paths: list[list[str]],
    column_names: list[str],
    sheet_name: str,
) -> dict[str, object]:
    """Build a full ChartSpec from a chart rule and data grid."""

    chart_type = str(chart_rule.get("chart_type", "bar"))
    title = str(chart_rule.get("title", ""))
    if not title:
        title = f"{sheet_name} - {_chart_type_label(chart_type)}"

    # Find dimension and measure columns
    dim_col: int | None = None
    measure_cols: list[int] = []

    for idx, kind in enumerate(column_kinds):
        if kind == "dimension" and dim_col is None:
            dim_col = idx
        elif kind == "measure":
            measure_cols.append(idx)

    if dim_col is None:
        dim_col = 0  # fallback

    if not measure_cols:
        measure_cols = [idx for idx in range(len(column_kinds)) if idx != dim_col]
        if not measure_cols:
            measure_cols = [dim_col]

    # Build series from data rows
    data_rows = aligned_grid[1:]
    x_data: list[object] = []
    series_list: list[dict[str, object]] = []
    y_field_names: list[str] = []

    for mc in measure_cols:
        y_name = column_names[mc] if mc < len(column_names) else f"col_{mc}"
        y_field_names.append(y_name)
        data: list[float | None] = []
        for row in data_rows:
            if mc < len(row):
                data.append(_safe_float(row[mc]))
            else:
                data.append(None)
        series_list.append({
            "name": y_name,
            "data": data,
        })

    # X-axis data
    for row in data_rows:
        if dim_col < len(row):
            x_data.append(row[dim_col])
        else:
            x_data.append("")

    # Source cells range
    header_row = 0
    data_start_row = 1
    data_end_row = len(aligned_grid) - 1
    min_col = min([dim_col] + measure_cols)
    max_col = max([dim_col] + measure_cols)
    source_cells = [_cell_range(header_row, min_col, data_end_row, max_col)]

    # Build filter conditions description
    filter_conditions = _build_filter_conditions(
        dim_col, measure_cols, column_names, data_rows,
    )

    # Highlight detection
    highlights = _detect_highlights(series_list)

    return {
        "chart_type": chart_type,
        "title": title,
        "x_field": column_names[dim_col] if dim_col < len(column_names) else "",
        "y_fields": y_field_names,
        "series": series_list,
        "highlights": highlights,
        "source_cells": source_cells,
        "filter_conditions": filter_conditions,
        "reason": str(chart_rule.get("source", "auto_infer")),
    }


def _build_filter_conditions(
    dim_col: int,
    measure_cols: list[int],
    column_names: list[str],
    data_rows: list[list[object]],
) -> str:
    """Build a human-readable filter conditions string."""
    dim_name = column_names[dim_col] if dim_col < len(column_names) else "维度"
    measure_names = [
        column_names[mc] if mc < len(column_names) else ""
        for mc in measure_cols
    ]
    measure_names = [n for n in measure_names if n]
    total_rows = len(data_rows)

    parts = [
        f"维度: {dim_name}",
        f"指标: {', '.join(measure_names) if measure_names else 'N/A'}",
        f"数据行数: {total_rows}",
    ]
    return "; ".join(parts)


def _detect_highlights(
    series_list: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Detect outlier data points for chart highlighting (z-score > 2)."""
    highlights: list[dict[str, object]] = []
    for si, s in enumerate(series_list):
        data = s.get("data", [])
        if not isinstance(data, list) or len(data) < 3:
            continue
        numeric: list[tuple[int, float]] = [
            (i, v) for i, v in enumerate(data) if isinstance(v, (int, float))
        ]
        if len(numeric) < 3:
            continue
        values = [v for _, v in numeric]
        mean_val = sum(values) / len(values)
        variance = sum((v - mean_val) ** 2 for v in values) / len(values)
        std_val = variance ** 0.5
        if std_val == 0:
            continue
        for idx, val in numeric:
            z = abs(val - mean_val) / std_val
            if z > 2.0:
                highlights.append({
                    "series_index": si,
                    "series_name": str(s.get("name", "")),
                    "data_index": idx,
                    "value": val,
                    "reason": (
                        f"z-score {z:.1f}, "
                        f"value {val} deviates from mean {mean_val:.1f}"
                    ),
                })
    return highlights


def _chart_type_label(chart_type: str) -> str:
    """Human-readable chart type label."""
    labels = {
        "bar": "柱状图",
        "line": "折线图",
        "pie": "饼图",
        "scatter": "散点图",
        "grouped_bar": "分组柱状图",
        "stacked_bar": "堆叠柱状图",
        "horizontal_bar": "条形图（排名）",
    }
    return labels.get(chart_type, chart_type)