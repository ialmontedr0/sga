from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.db.seed import seed_database
from judicial_archive.modules.boxes.models import Box
from judicial_archive.modules.courts.models import (
    Court,
    NumberingPolicy,
    PartyRole,
    SystemSetting,
)
from judicial_archive.modules.locations.models import Area, Shelf
from judicial_archive.modules.users.models import Role

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_seed_is_idempotent(db_session: AsyncSession) -> None:
    await seed_database(db_session)
    await seed_database(db_session)

    async def count(model: type[Any]) -> int:
        value = await db_session.scalar(select(func.count()).select_from(model))
        assert value is not None
        return int(value)

    assert await count(Role) == 5
    assert await count(Area) == 5
    assert await count(Shelf) == 39
    assert await count(Court) == 8
    assert await count(PartyRole) == 1
    assert await count(NumberingPolicy) == 1
    assert await count(SystemSetting) == 1

    duplicates_589 = await db_session.scalar(
        select(func.count()).select_from(Court).where(Court.code_raw == "589")
    )
    duplicates_107 = await db_session.scalar(
        select(func.count()).select_from(Court).where(Court.code_raw == "107")
    )
    assert duplicates_589 == 2
    assert duplicates_107 == 2


@pytest.mark.asyncio
async def test_seed_does_not_create_operational_data(db_session: AsyncSession) -> None:
    await seed_database(db_session)
    boxes = await db_session.scalar(select(func.count()).select_from(Box))
    assert boxes == 0
