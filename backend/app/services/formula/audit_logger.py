"""Day 14 structured audit logger — JSON Lines format for inference pipeline."""

from __future__ import annotations

import json
import logging
import time

logger = logging.getLogger("formula_audit")


def log_inference_start(task_id: int, sheet_count: int, model_name: str) -> float:
    """Log inference start and return monotonic timestamp for duration calculation."""
    logger.info(
        json.dumps(
            {
                "event": "formula_inference_start",
                "task_id": task_id,
                "sheet_count": sheet_count,
                "model_name": model_name,
            },
            ensure_ascii=False,
        ),
    )
    return time.monotonic()


def log_inference_complete(
    task_id: int,
    start_ts: float,
    accepted: int,
    rejected: int,
    confidences: list[float],
    rejection_reasons: dict[str, int],
) -> None:
    """Log inference completion with duration, confidence distribution, and rejection breakdown."""
    duration_ms = round((time.monotonic() - start_ts) * 1000)

    if confidences:
        sorted_conf = sorted(confidences)
        p50_index = int(len(sorted_conf) * 0.5)
        p90_index = int(len(sorted_conf) * 0.9)
        confidence_p50 = sorted_conf[min(p50_index, len(sorted_conf) - 1)]
        confidence_p90 = sorted_conf[min(p90_index, len(sorted_conf) - 1)]
    else:
        confidence_p50 = 0.0
        confidence_p90 = 0.0

    logger.info(
        json.dumps(
            {
                "event": "formula_inference_complete",
                "task_id": task_id,
                "duration_ms": duration_ms,
                "accepted": accepted,
                "rejected": rejected,
                "confidence_p50": confidence_p50,
                "confidence_p90": confidence_p90,
                "rejection_reasons": rejection_reasons,
            },
            ensure_ascii=False,
        ),
    )
