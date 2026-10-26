from __future__ import annotations

import os
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

import judicial_archive.models  # noqa: F401
from judicial_archive.db.base import Base

BACKEND_ROOT = Path(__file__).resolve().parents[2]


class _RedactedDatabaseUrl(str):
    def __repr__(self) -> str:
        return "<TEST_DATABASE_URL>"


def _integration_url() -> str:
    if os.getenv("RUN_INTEGRATION") != "1":
        pytest.skip("RUN_INTEGRATION=1 no está definido")
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL no está definido")
    if "prod" in url.lower():
        pytest.skip("La URL parece de producción; se rechaza por seguridad")
    return _RedactedDatabaseUrl(url)


@pytest.fixture(scope="session")
def test_database_url() -> str:
    return _integration_url()


@pytest.fixture(scope="session")
def alembic_config(test_database_url: str) -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option(
        "script_location",
        (BACKEND_ROOT / "alembic").as_posix(),
    )
    config.set_main_option(
        "sqlalchemy.url",
        test_database_url.replace("%", "%%"),
    )
    return config


@pytest.fixture(scope="session")
def migrated_database(
    alembic_config: Config,
    test_database_url: str,
) -> str:
    command.upgrade(alembic_config, "head")
    return test_database_url


@pytest_asyncio.fixture
async def db_engine(migrated_database: str) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(migrated_database, poolclass=NullPool)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def session_factory(
    db_engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    factory = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    table_names = ", ".join(f'"{table.name}"' for table in reversed(Base.metadata.sorted_tables))
    async with db_engine.begin() as connection:
        await connection.execute(
            text("ALTER TABLE audit_events DISABLE TRIGGER trg_audit_events_no_truncate")
        )
        try:
            await connection.execute(text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE"))
            await connection.execute(
                text("ALTER SEQUENCE box_visible_number_seq RESTART WITH 4402")
            )
        finally:
            await connection.execute(
                text("ALTER TABLE audit_events ENABLE TRIGGER trg_audit_events_no_truncate")
            )
    return factory


@pytest_asyncio.fixture
async def db_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.rollback()
