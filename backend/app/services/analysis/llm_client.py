"""Day 20 - LLM client for analysis.

Mockable HTTP client. Follows same pattern as Day 13 llm_formula_client.
"""

from __future__ import annotations

import json
from urllib import request
from urllib.error import URLError

from app.core.config import settings

ANALYSIS_TIMEOUT_SECONDS = 60


def call_analysis_llm(
    *,
    system_prompt: str,
    user_prompt: str,
    model_name: str | None = None,
) -> dict[str, object]:
    """Call the LLM API for analysis.

    Raises RuntimeError on network/API failures.
    """
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

    # Extract content from OpenAI-compatible response format
    choices = body.get("choices", [])
    if not choices:
        raise RuntimeError("LLM API returned empty choices")

    content = choices[0].get("message", {}).get("content", "")
    if not content:
        raise RuntimeError("LLM API returned empty content")

    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"LLM response content is not valid JSON: {exc}") from exc