"""Day 20 - LLM client for analysis. Supports mock mode."""

from __future__ import annotations

import json
from pathlib import Path
from urllib import request
from urllib.error import URLError

from app.core.config import settings

ANALYSIS_TIMEOUT_SECONDS = 60

_MOCK_DATA: dict[str, object] | None = None


def _load_mock() -> dict[str, object]:
    global _MOCK_DATA
    if _MOCK_DATA is not None:
        return _MOCK_DATA
    fixture = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "mock_insights.json"
    if fixture.exists():
        _MOCK_DATA = json.loads(fixture.read_text(encoding="utf-8"))
    else:
        _MOCK_DATA = {
            "insights": [
                {
                    "title": "数据质量良好",
                    "description": "未发现异常数据（Mock 模式）",
                    "severity": "low",
                    "evidence": [],
                    "needs_human_review": False,
                }
            ]
        }
    return _MOCK_DATA


def call_analysis_llm(
    *,
    system_prompt: str,
    user_prompt: str,
    model_name: str | None = None,
) -> dict[str, object]:
    """Call the LLM API for analysis, or return mock data."""

    if settings.llm_mock_mode:
        return _load_mock()

    model = model_name or settings.analysis_llm_model
    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "response_format": {"type": "json_object"},
    }).encode("utf-8")

    req = request.Request(
        settings.analysis_llm_api_url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.analysis_llm_api_key}",
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=ANALYSIS_TIMEOUT_SECONDS) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except URLError as exc:
        raise RuntimeError(f"LLM API call failed: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"LLM API returned invalid JSON: {exc}") from exc

    return body
