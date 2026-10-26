from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_sequence_is_unique_under_concurrency(
    db_engine: AsyncEngine,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    court_id = uuid4()
    async with db_engine.begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO courts "
                "(id, code_raw, code_normalized, name, status) "
                "VALUES (:id, '102', '102', 'Corte de Apelación', 'ACTIVE')"
            ),
            {"id": court_id},
        )

    async def allocate() -> int:
        async with session_factory() as session:
            number = await session.scalar(text("SELECT nextval('box_visible_number_seq')"))
            await session.execute(
                text(
                    "INSERT INTO boxes "
                    "(id, court_id, year, visible_number) "
                    "VALUES (:id, :court_id, 2026, :number)"
                ),
                {
                    "id": uuid4(),
                    "court_id": court_id,
                    "number": str(number),
                },
            )
            await session.commit()
            return int(number)

    values = await asyncio.gather(*(allocate() for _ in range(20)))

    assert len(values) == 20
    assert len(set(values)) == 20
    assert min(values) >= 4402
    assert max(values) <= 4421
