from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

pytestmark = pytest.mark.integration


async def _insert_event(connection: AsyncConnection) -> None:
    await connection.execute(
        text(
            "INSERT INTO audit_events "
            "(id, actor_type, action, entity_type, source, result) "
            "VALUES (:id, 'SYSTEM', 'BOOT', 'system', 'SYSTEM', 'SUCCESS')"
        ),
        {"id": uuid4()},
    )


@pytest.mark.asyncio
async def test_audit_event_cannot_be_updated(db_engine: AsyncEngine) -> None:
    async with db_engine.connect() as connection:
        transaction = await connection.begin()
        await _insert_event(connection)
        with pytest.raises(DBAPIError, match="append-only"):
            await connection.execute(text("UPDATE audit_events SET action = 'CHANGED'"))
        await transaction.rollback()


@pytest.mark.asyncio
async def test_audit_event_cannot_be_deleted(db_engine: AsyncEngine) -> None:
    async with db_engine.connect() as connection:
        transaction = await connection.begin()
        await _insert_event(connection)
        with pytest.raises(DBAPIError, match="append-only"):
            await connection.execute(text("DELETE FROM audit_events"))
        await transaction.rollback()


@pytest.mark.asyncio
async def test_audit_event_cannot_be_truncated(db_engine: AsyncEngine) -> None:
    async with db_engine.connect() as connection:
        transaction = await connection.begin()
        await _insert_event(connection)
        with pytest.raises(DBAPIError, match="append-only"):
            await connection.execute(text("TRUNCATE audit_events"))
        await transaction.rollback()
