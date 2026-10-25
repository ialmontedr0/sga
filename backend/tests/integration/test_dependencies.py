from __future__ import annotations

import os

import pytest
from redis.asyncio import Redis
from sqlalchemy import text

from judicial_archive.db.session import Database
from tests.helpers import build_test_settings

_RUN_INTEGRATION = os.getenv("RUN_INTEGRATION") == "1"
_INTEGRATION_REASON = "Definir RUN_INTEGRATION=1 y disponer de PostgreSQL/Redis."


@pytest.mark.integration
@pytest.mark.skipif(not _RUN_INTEGRATION, reason=_INTEGRATION_REASON)
async def test_postgresql_connection() -> None:
    settings = build_test_settings(
        database_url=os.getenv("TEST_DATABASE_URL")
        or os.getenv(
            "SGA_DATABASE_URL",
            "postgresql+psycopg://sga_test:sga_test@localhost:5432/sga_test",
        )
    )
    database = Database(settings)
    try:
        async with database.engine.connect() as connection:
            result = await connection.execute(text("SELECT 1"))
            assert result.scalar_one() == 1
    finally:
        await database.dispose()


@pytest.mark.integration
@pytest.mark.skipif(not _RUN_INTEGRATION, reason=_INTEGRATION_REASON)
async def test_redis_connection() -> None:
    settings = build_test_settings(
        redis_url=os.getenv("TEST_REDIS_URL")
        or os.getenv("SGA_REDIS_URL", "redis://localhost:6379/15")
    )
    redis: Redis = Redis.from_url(  # pyright: ignore[reportUnknownMemberType]
        str(settings.redis_url),
        encoding="utf-8",
        decode_responses=True,
    )
    try:
        assert await redis.ping() is True  # pyright: ignore[reportUnknownMemberType]
    finally:
        await redis.aclose()
