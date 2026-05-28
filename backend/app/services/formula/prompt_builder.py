"""Prompt construction for high-precision Day 13 formula inference."""

from __future__ import annotations

import json

PROMPT_VERSION = "day13_v1"
MAX_SAMPLE_ROWS = 6


def build_formula_inference_prompt(
    task_id: int,
    sheets: list[dict[str, object]],
    max_candidates_per_sheet: int,
) -> str:
    prompt_payload = {
        "task_id": task_id,
        "prompt_version": PROMPT_VERSION,
        "rules": {
            "json_only": True,
            "no_new_columns": True,
            "max_candidates_per_sheet": max_candidates_per_sheet,
            "prefer_empty_over_guessing": True,
            "accepted_dsl_examples": [
                "col_Profit = col_Revenue - col_Cost",
                "row_Total = sum(row_A:row_C)",
            ],
        },
        "sheets": [_build_sheet_prompt_payload(sheet) for sheet in sheets],
    }

    return (
        "You are inferring spreadsheet formulas.\n"
        "Only use the provided columns and rows.\n"
        "Return JSON only.\n"
        "If uncertain, return an empty candidate list.\n\n"
        f"{json.dumps(prompt_payload, ensure_ascii=False, indent=2)}"
    )


def _build_sheet_prompt_payload(sheet: dict[str, object]) -> dict[str, object]:
    aligned_grid = sheet.get("aligned_grid", [])
    sample_rows = aligned_grid[:MAX_SAMPLE_ROWS] if isinstance(aligned_grid, list) else []

    return {
        "sheet_id": sheet["sheet_id"],
        "sheet_name": sheet["sheet_name"],
        "column_paths": sheet["column_paths"],
        "column_kinds": sheet["column_kinds"],
        "sample_rows": sample_rows,
    }
