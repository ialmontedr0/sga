from __future__ import annotations

import asyncio
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request, Response, status
from pydantic import BaseModel, Field
from redis.asyncio import Redis

from judicial_archive import __version__
from judicial_archive.api.deps import get_app_settings
from judicial_archive.core.config import Settings
from judicial_archive.db.health import check_database, check_redis
from judicial_archive.db.session import Database

router = APIRouter()


class LivenessStatus(BaseModel):
    status: Literal["ok"] = "ok"
    service: str
    version: str
    environment: str


class ComponentHealth(BaseModel):
    status: Literal["ok", "error"]
    latency_ms: float = Field(ge=0)


class ReadinessStatus(BaseModel):
    status: Literal["ok", "error"]
    version: str
    components: dict[str, ComponentHealth]


@router.get(
    "/live",
    response_model=LivenessStatus,
    summary="Verificar que el proceso responde",
)
async def liveness(
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> LivenessStatus:
    return LivenessStatus(
        service=settings.app_name,
        version=__version__,
        environment=settings.environment.value,
    )


@router.get(
    "/ready",
    response_model=ReadinessStatus,
    responses={503: {"model": ReadinessStatus}},
    summary="Verificar disponibilidad de dependencias",
)
async def readiness(
    request: Request,
    response: Response,
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> ReadinessStatus:
    database: Database | None = getattr(request.app.state, "database", None)
    redis: Redis | None = getattr(request.app.state, "redis", None)
    db_health, redis_health = await asyncio.gather(
        check_database(database, settings.readiness_timeout_seconds),
        check_redis(redis, settings.readiness_timeout_seconds),
    )
    components = {
        "database": ComponentHealth(
            status=db_health.status,
            latency_ms=db_health.latency_ms,
        ),
        "redis": ComponentHealth(
            status=redis_health.status,
            latency_ms=redis_health.latency_ms,
        ),
    }
    is_ready = all(component.status == "ok" for component in components.values())
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessStatus(
        status="ok" if is_ready else "error",
        version=__version__,
        components=components,
    )
