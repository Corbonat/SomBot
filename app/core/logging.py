from __future__ import annotations

import logging
import sys
from typing import Any, Dict

import structlog


def setup_logging(level: str = "INFO") -> None:
    """Configure structlog + stdlib logging."""
    level_value = getattr(logging, level.upper(), logging.INFO)
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            timestamper,
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level_value),
        context_class=dict,
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level_value,
    )


def get_logger(name: str, **bind_kwargs: Dict[str, Any]) -> structlog.BoundLogger:
    return structlog.get_logger(name, **bind_kwargs)
