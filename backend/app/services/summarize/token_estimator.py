"""Day 19 - token estimator.

Approximates token count for mixed Chinese/English JSON.
Rough estimate: 1 token per 3.5 characters (conservative for CJK).
"""

from __future__ import annotations

import json

CHARS_PER_TOKEN = 3.5
DEFAULT_TOKEN_BUDGET = 4000


def estimate_tokens(data: object) -> int:
    """Estimate token count for a JSON-serializable object."""
    text = json.dumps(data, ensure_ascii=False, default=str)
    return max(1, int(len(text) / CHARS_PER_TOKEN))


def estimate_tokens_from_string(text: str) -> int:
    """Estimate token count from a raw string."""
    return max(1, int(len(text) / CHARS_PER_TOKEN))