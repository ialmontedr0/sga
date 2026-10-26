from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import cast

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from judicial_archive import __version__
from judicial_archive.api.v1.router import api_router
from judicial_archive.core.config import Environment, Settings, get_settings
from judicial_archive.core.errors import register_exception_handlers
from judicial_archive.core.logging import configure_logging
from judicial_archive.core.middleware import (
    RequestBodyLimitMiddleware,
    RequestContextMiddleware,
    TrustedHostMiddleware,
)
from judicial_archive.core.runtime import configure_event_loop_policy
from judicial_archive.db.session import Database

configure_event_loop_policy()

logger = structlog.get_logger(__name__)

_OPENAPI_TAGS = [
    {"name": "Salud", "description": "Disponibilidad del proceso y de sus dependencias"}
]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    settings = cast(Settings, app.state.settings)
    database = Database(settings)
    redis: Redis = Redis.from_url(  # pyright: ignore[reportUnknownMemberType]
        str(settings.redis_url),
        encoding="utf-8",
        decode_responses=True,
        socket_connect_timeout=settings.redis_socket_timeout_seconds,
        socket_timeout=settings.redis_socket_timeout_seconds,
    )
    app.state.database = database
    app.state.redis = redis

    logger.info(
        "application_starting",
        environment=settings.environment.value,
        version=__version__,
    )
    try:
        yield
    finally:
        await redis.aclose()
        await database.dispose()
        logger.info("application_stopped")


def create_app(settings: Settings | None = None, *, configure_logs: bool = True) -> FastAPI:
    resolved_settings = settings or get_settings()
    if configure_logs:
        configure_logging(resolved_settings)

    docs_enabled = resolved_settings.docs_enabled
    app = FastAPI(
        title=resolved_settings.app_name,
        description="API del Sistema de Gestion Documental Judicial.",
        version=__version__,
        debug=(
            resolved_settings.debug and resolved_settings.environment is Environment.DEVELOPMENT
        ),
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
        openapi_tags=_OPENAPI_TAGS,
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings

    register_exception_handlers(app)
    app.include_router(api_router, prefix=resolved_settings.api_v1_prefix)

    # El ultimo middleware agregado es el mas externo.
    app.add_middleware(
        RequestBodyLimitMiddleware,
        max_bytes=resolved_settings.max_request_body_bytes,
    )

    if resolved_settings.trusted_hosts:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=resolved_settings.trusted_hosts,
        )

    if resolved_settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=resolved_settings.cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=[
                "Authorization",
                "Content-Type",
                resolved_settings.csrf_header_name,
                resolved_settings.request_id_header,
            ],
            expose_headers=[resolved_settings.request_id_header],
            max_age=600,
        )

    app.add_middleware(
        RequestContextMiddleware,
        header_name=resolved_settings.request_id_header,
    )

    return app
