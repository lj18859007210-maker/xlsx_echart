"""HTTP client wrapper for Day 13 formula inference. Supports mock mode."""

from __future__ import annotations

import json
from pathlib import Path
from urllib import request

from app.core.config import settings

_MOCK_DATA: dict[str, object] | None = None


def _load_mock() -> dict[str, object]:
    global _MOCK_DATA
    if _MOCK_DATA is not None:
        return _MOCK_DATA
    fixture = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "mock_formula_rules.json"
    if fixture.exists():
        _MOCK_DATA = json.loads(fixture.read_text(encoding="utf-8"))
    else:
        _MOCK_DATA = {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "sheet_candidates": [{
                            "sheet_id": 1,
                            "candidates": [
                                {"formula_text": "=SUM(B2:B10)", "confidence": 0.9, "rationale": "求和区域（Mock）"},
                            ]
                        }]
                    })
                }
            }]
        }
    return _MOCK_DATA


def build_formula_inference_request_payload(prompt: str, model_name: str) -> dict[str, object]:
    return {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"},
    }


def run_formula_inference(*, prompt: str, model_name: str) -> dict[str, object]:
    if settings.llm_mock_mode:
        return _load_mock()

    payload = json.dumps(
        build_formula_inference_request_payload(prompt, model_name),
    ).encode("utf-8")
    req = request.Request(
        settings.formula_llm_api_url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.formula_llm_api_key}",
        },
        method="POST",
    )
    with request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))
