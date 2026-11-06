from __future__ import annotations

import asyncio
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from judicial_archive.modules.courts.models import Court
from judicial_archive.modules.numbering.services import allocate_visible_number

pytestmark = pytest.mark.integration


async def _allocate(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    court_id: UUID,
    year: int,
) -> str:
    async with session_factory() as session:
        value, _policy = await allocate_visible_number(
            session,
            court_id=court_id,
            box_type="EXPEDIENTES",
            year=year,
        )
        await session.commit()
        return value


@pytest.mark.asyncio
async def test_concurrent_number_allocation_is_unique(
    seeded_api_client: TestClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        court = await session.scalar(select(Court).where(Court.status == "ACTIVE").limit(1))
        assert court is not None
        court_id = court.id

    values = await asyncio.gather(
        *[_allocate(session_factory, court_id=court_id, year=2026) for _ in range(20)]
    )

    assert len(values) == 20
    assert len(set(values)) == 20


@pytest.mark.asyncio
async def test_concurrent_number_allocation_keeps_sequence_monotonic(
    seeded_api_client: TestClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        court = await session.scalar(select(Court).where(Court.status == "ACTIVE").limit(1))
        assert court is not None
        court_id = court.id

    values = await asyncio.gather(
        *[_allocate(session_factory, court_id=court_id, year=2026) for _ in range(10)]
    )

    numeric_values = sorted(int(value) for value in values)
    assert numeric_values == list(range(numeric_values[0], numeric_values[0] + 10))
