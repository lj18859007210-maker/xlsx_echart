"""Day 21 ChartSpec builder."""

from __future__ import annotations


def _col_letter(idx: int) -> str:
    result = ""
    n = idx
    while n >= 0:
        result = chr(65 + (n % 26)) + result
        n = n // 26 - 1
    return result


def _cell_range(start_row: int, start_col: int, end_row: int, end_col: int) -> str:
    return f"{_col_letter(start_col)}{start_row + 1}:{_col_letter(end_col)}{end_row + 1}"


def _safe_float(val: object) -> float | None:
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


def build_chart_spec(chart_rule, aligned_grid, column_kinds, column_paths, column_names, sheet_name):
    chart_type = str(chart_rule.get("chart_type", "bar"))
    title = str(chart_rule.get("title", ""))
    if not title:
        title = f"{sheet_name} - {_chart_type_label(chart_type)}"

    dim_col = None
    measure_cols = []
    for idx, kind in enumerate(column_kinds):
        if kind == "dimension" and dim_col is None:
            dim_col = idx
        elif kind == "measure":
            measure_cols.append(idx)

    if dim_col is None:
        dim_col = 0

    if not measure_cols:
        measure_cols = [idx for idx in range(len(column_kinds)) if idx != dim_col]
        if not measure_cols:
            measure_cols = [dim_col]

    data_rows = aligned_grid[1:]
    x_data = []
    series_list = []
    y_field_names = []

    for mc in measure_cols:
        y_name = column_names[mc] if mc < len(column_names) else f"col_{mc}"
        y_field_names.append(y_name)
        data = []
        for row in data_rows:
            if mc < len(row):
                data.append(_safe_float(row[mc]))
            else:
                data.append(None)
        series_list.append({"name": y_name, "data": data})

    for row in data_rows:
        if dim_col < len(row):
            x_data.append(row[dim_col])
        else:
            x_data.append("")

    header_row = 0
    data_end_row = len(aligned_grid) - 1
    min_col = min([dim_col] + measure_cols)
    max_col = max([dim_col] + measure_cols)
    source_cells = [_cell_range(header_row, min_col, data_end_row, max_col)]

    filter_conditions = _build_filter_conditions(dim_col, measure_cols, column_names, data_rows)
    highlights = _detect_highlights(series_list)

    return {
        "chart_type": chart_type,
        "title": title,
        "x_field": column_names[dim_col] if dim_col < len(column_names) else "",
        "x_data": x_data,
        "y_fields": y_field_names,
        "series": series_list,
        "highlights": highlights,
        "source_cells": source_cells,
        "filter_conditions": filter_conditions,
        "reason": str(chart_rule.get("source", "auto_infer")),
    }


def _build_filter_conditions(dim_col, measure_cols, column_names, data_rows):
    dim_name = column_names[dim_col] if dim_col < len(column_names) else "dim"
    measure_names = [column_names[mc] if mc < len(column_names) else "" for mc in measure_cols]
    measure_names = [n for n in measure_names if n]
    total_rows = len(data_rows)
    parts = [f"dim: {dim_name}", f"metrics: {', '.join(measure_names) if measure_names else 'N/A'}", f"rows: {total_rows}"]
    return " | ".join(parts)


def _detect_highlights(series_list):
    highlights = []
    for si, s in enumerate(series_list):
        data = s.get("data", [])
        if not isinstance(data, list) or len(data) < 3:
            continue
        numeric = [(i, v) for i, v in enumerate(data) if isinstance(v, (int, float))]
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
                    "reason": f"z={z:.1f}, val={val} vs mean={mean_val:.1f}",
                })
    return highlights


def _chart_type_label(chart_type: str) -> str:
    labels = {
        "bar": "Bar",
        "line": "Line",
        "pie": "Pie",
        "scatter": "Scatter",
        "grouped_bar": "Grouped Bar",
        "stacked_bar": "Stacked Bar",
        "horizontal_bar": "Horizontal Bar",
    }
    return labels.get(chart_type, chart_type)
