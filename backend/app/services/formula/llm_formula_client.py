"""HTTP client wrapper for Day 13 formula inference."""

from __future__ import annotations

import json
from urllib import request

from app.core.config import settings


def build_formula_inference_request_payload(prompt: str, model_name: str) -> dict[str, object]:
    return {
        "model": model_name,
        "prompt": prompt,
        "response_format": {"type": "json_object"},
    }


def run_formula_inference(*, prompt: str, model_name: str) -> dict[str, object]:
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
