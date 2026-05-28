"""Day 21 ECharts adapter — converts ChartSpec to ECharts option JSON.

Frontend can consume this output directly with ECharts's setOption().
"""

from __future__ import annotations


def to_echarts_option(spec: dict[str, object]) -> dict[str, object]:
    """Convert a ChartSpec dict into a minimal ECharts option object.

    The returned dict can be passed to echarts.setOption() after frontend
    applies any theme / responsive adjustments.
    """
    chart_type = str(spec.get("chart_type", "bar"))
    title_text = str(spec.get("title", ""))
    x_field = str(spec.get("x_field", ""))
    y_fields = spec.get("y_fields", [])
    series_data = spec.get("series", [])
    highlights = spec.get("highlights", [])

    # Map our chart_type to ECharts series type
    type_map = {
        "bar": "bar",
        "grouped_bar": "bar",
        "stacked_bar": "bar",
        "horizontal_bar": "bar",
        "line": "line",
        "pie": "pie",
        "scatter": "scatter",
    }
    echarts_series_type = type_map.get(chart_type, "bar")

    echarts_option: dict[str, object] = {
        "title": {"text": title_text, "left": "center"},
        "tooltip": {"trigger": "axis" if chart_type != "pie" else "item"},
        "legend": {
            "data": [s.get("name", "") for s in series_data if isinstance(s, dict)],
            "bottom": 0,
        },
        "xAxis": {
            "type": "category",
            "name": x_field,
            "data": _build_x_data(spec),
        },
        "yAxis": {"type": "value"},
        "series": [],
    }

    if chart_type == "pie":
        echarts_option.pop("xAxis", None)
        echarts_option.pop("yAxis", None)
        echarts_option["series"] = [{
            "type": "pie",
            "name": str(title_text),
            "radius": "60%",
            "data": _build_pie_data(series_data),
        }]
    elif chart_type == "horizontal_bar":
        # Swap x/y axis
        echarts_option["yAxis"] = echarts_option.pop("xAxis")
        echarts_option["xAxis"] = {"type": "value"}
        for s in series_data:
            if isinstance(s, dict):
                echarts_option["series"].append({
                    "type": "bar",
                    "name": str(s.get("name", "")),
                    "data": list(s.get("data", [])),
                })
        echarts_option["legend"]["data"] = [
            s.get("name", "") for s in series_data if isinstance(s, dict)
        ]
    elif chart_type == "stacked_bar":
        for s in series_data:
            if isinstance(s, dict):
                echarts_option["series"].append({
                    "type": "bar",
                    "name": str(s.get("name", "")),
                    "data": list(s.get("data", [])),
                    "stack": "total",
                })
    else:
        for s in series_data:
            if isinstance(s, dict):
                echarts_option["series"].append({
                    "type": echarts_series_type,
                    "name": str(s.get("name", "")),
                    "data": list(s.get("data", [])),
                })

    # Mark highlights
    if highlights:
        echarts_option["_highlights"] = list(highlights)

    return echarts_option


def _build_x_data(spec: dict[str, object]) -> list[object]:
    """Extract x-axis data from spec's x_field + series."""
    series_data = spec.get("series", [])
    if not isinstance(series_data, list) or not series_data:
        return []
    first_series = series_data[0]
    if not isinstance(first_series, dict):
        return []
    data = first_series.get("data", [])
    if not isinstance(data, list):
        return []
    return list(range(len(data)))


def _build_pie_data(
    series_data: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Build pie chart data from series."""
    result: list[dict[str, object]] = []
    for s in series_data:
        if isinstance(s, dict):
            name = str(s.get("name", ""))
            data = s.get("data", [])
            if isinstance(data, list):
                for i, val in enumerate(data):
                    result.append({
                        "name": str(i) if name else str(i),
                        "value": val,
                    })
    return result


def supports_chart_type(chart_type: str) -> bool:
    """Check whether a chart type can be rendered by ECharts adapter."""
    return chart_type in {
        "bar", "line", "pie", "scatter",
        "grouped_bar", "stacked_bar", "horizontal_bar",
    }