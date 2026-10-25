from __future__ import annotations

from typing import Any, ClassVar

import structlog
from arq.connections import RedisSettings

from judicial_archive.core.config import get_settings
from judicial_archive.core.runtime import configure_event_loop_policy

configure_event_loop_policy()

logger = structlog.get_logger(__name__)
_settings = get_settings()


async def startup(ctx: dict[Any, Any]) -> None:
    logger.info(
        "worker_started",
        queue=_settings.task_queue_name,
        max_jobs=_settings.task_max_jobs,
    )


async def shutdown(ctx: dict[Any, Any]) -> None:
    logger.info("worker_stopped")


async def healthcheck(ctx: dict[Any, Any]) -> dict[str, str]:
    """Tarea minima de diagnostico para que ARQ pueda arrancar en B0."""
    logger.info("worker_healthcheck")
    return {"status": "ok"}


class WorkerSettings:
    """Configuracion de ARQ."""

    functions: ClassVar[list[Any]] = [healthcheck]
    on_startup: Any = startup
    on_shutdown: Any = shutdown
    redis_settings: RedisSettings = RedisSettings.from_dsn(str(_settings.redis_url))
    queue_name: str = _settings.task_queue_name
    max_jobs: int = _settings.task_max_jobs
    job_timeout: int = _settings.task_job_timeout_seconds
