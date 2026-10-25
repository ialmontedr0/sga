from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor

from judicial_archive.core.config import Settings

_SENSITIVE_KEY_MARKERS = frozenset(
    {
        "password",
        "passwd",
        "secret",
        "token",
        "authorization",
        "cookie",
        "api_key",
        "apikey",
        "session",
    }
)


def _redact_sensitive_values(
    _logger: Any,
    _method_name: str,
    event_dict: EventDict,
) -> EventDict:
    """Reemplaza valores de claves sensibles antes de emitir el log."""
    for key in list(event_dict):
        if any(marker in key.lower() for marker in _SENSITIVE_KEY_MARKERS):
            event_dict[key] = "***"
    return event_dict


def _shared_processors() -> list[Processor]:
    return [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        _redact_sensitive_values,
    ]


def configure_logging(settings: Settings) -> None:
    """Configura structlog y el logging estandar de forma unificada."""
    shared_processors = _shared_processors()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    renderer: Processor
    if settings.log_json:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=renderer,
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(settings.log_level)

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uv_logger = logging.getLogger(logger_name)
        uv_logger.handlers.clear()
        uv_logger.propagate = True
