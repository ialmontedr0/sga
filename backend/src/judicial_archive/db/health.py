from __future__ import annotations

import asyncio
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Literal, Protocol

import structlog
from sqlalchemy import text

from judicial_archive.db.session import Database

HealthState = Literal["ok", "error"]


class RedisPing(Protocol):
    """Contrato minimo de Redis usado por salud; facilita pruebas."""

    def ping(self, **kwargs: Any) -> Any: ...


@dataclass(frozen=True, slots=True)
class DependencyHealth:
    status: HealthState
    latency_ms: float


logger = structlog.get_logger(__name__)


def _elapsed_ms(started: float) -> float:
    return round((perf_counter() - started) * 1000, 2)


async def check_database(
    database: Database | None,
    timeout_seconds: float,
) -> DependencyHealth:
    started = perf_counter()
    if database is None:
        logger.warning("database_health_check_unavailable")
        return DependencyHealth(status="error", latency_ms=0.0)
    try:
        async with asyncio.timeout(timeout_seconds):
            async with database.engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
    except Exception as exc:
        logger.warning(
            "database_health_check_failed",
            error_type=type(exc).__name__,
        )
        return DependencyHealth(status="error", latency_ms=_elapsed_ms(started))
    return DependencyHealth(status="ok", latency_ms=_elapsed_ms(started))


async def check_redis(
    redis: RedisPing | None,
    timeout_seconds: float,
) -> DependencyHealth:
    started = perf_counter()
    if redis is None:
        logger.warning("redis_health_check_unavailable")
        return DependencyHealth(status="error", latency_ms=0.0)
    try:
        async with asyncio.timeout(timeout_seconds):
            await redis.ping()
    except Exception as exc:
        logger.warning(
            "redis_health_check_failed",
            error_type=type(exc).__name__,
        )
        return DependencyHealth(status="error", latency_ms=_elapsed_ms(started))
    return DependencyHealth(status="ok", latency_ms=_elapsed_ms(started))
