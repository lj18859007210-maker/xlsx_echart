"""Structured logging with structlog."""

from __future__ import annotations

import logging
import sys
from contextvars import ContextVar
from pathlib import Path
from typing import Any

import structlog

from app.core.config import settings

_task_id_var: ContextVar[str | None] = ContextVar("task_id", default=None)


def set_task_id(task_id: str | None) -> None:
    _task_id_var.set(task_id)


def get_task_id() -> str | None:
    return _task_id_var.get()


def _add_task_id(_logger: Any, _method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    tid = get_task_id()
    if tid is not None:
        event_dict["task_id"] = tid
    return event_dict


def setup_logging() -> None:
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    timestamper = structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S", utc=False)

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        _add_task_id,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        timestamper,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.app_debug:
        structlog.configure(
            processors=shared_processors + [
                structlog.dev.ConsoleRenderer(colors=True),
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
    else:
        json_file = log_dir / "app.log"
        structlog.configure(
            processors=shared_processors + [
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            context_class=dict,
            logger_factory=structlog.WriteLoggerFactory(file=json_file.open("a", encoding="utf-8")),
            cache_logger_on_first_use=True,
        )

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name or __name__)
