from __future__ import annotations

from dataclasses import dataclass
from typing import cast
from uuid import UUID, uuid4

import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette.requests import Request

from judicial_archive.core.enums import CustodyStatus
from judicial_archive.modules.boxes.models import Box
from judicial_archive.modules.courts.models import Court
from judicial_archive.modules.locations.models import Area, Position, Shelf, Tray

NO_REQUEST = cast(Request, None)


@dataclass(frozen=True)
class LocationTree:
    area_id: UUID
    shelf_id: UUID
    tray_id: UUID
    position_ids: tuple[UUID, ...]
    box_ids: tuple[UUID, ...]


async def create_location_tree(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    positions: int = 3,
    boxes: int = 2,
) -> LocationTree:
    async with session_factory() as session:
        court = await session.scalar(select(Court).limit(1))
        if court is None:
            suffix = uuid4().hex[:8].upper()
            court = Court(
                code_raw=f"B6{suffix}",
                code_normalized=f"B6{suffix}",
                name="Juzgado B6",
            )
            session.add(court)
            await session.flush()
        else:
            suffix = uuid4().hex[:8].upper()

        area = Area(code=f"A{suffix}", name="Area B6", status="ACTIVE")
        session.add(area)
        await session.flush()

        shelf = Shelf(
            area_id=area.id,
            code=f"S{suffix}",
            name="Anaquel B6",
            levels=1,
            positions_per_level=positions,
            status="ACTIVE",
        )
        session.add(shelf)
        await session.flush()

        tray = Tray(
            shelf_id=shelf.id,
            code=f"T{suffix}",
            name="Bandeja B6",
            status="ACTIVE",
        )
        session.add(tray)
        await session.flush()

        position_rows = [
            Position(
                tray_id=tray.id,
                code=f"P{index:02d}",
                label=f"Posicion {index}",
                status="AVAILABLE",
            )
            for index in range(1, positions + 1)
        ]
        session.add_all(position_rows)
        await session.flush()

        box_rows = [
            Box(
                court_id=court.id,
                year=2026,
                box_type="EXPEDIENTES",
                visible_number=f"B6-{suffix}-{index}",
                lifecycle_status="ACTIVE",
                custody_status=CustodyStatus.UNKNOWN.value,
                confidentiality="INTERNAL",
                created_by=None,
            )
            for index in range(1, boxes + 1)
        ]
        session.add_all(box_rows)
        await session.commit()

        return LocationTree(
            area_id=area.id,
            shelf_id=shelf.id,
            tray_id=tray.id,
            position_ids=tuple(row.id for row in position_rows),
            box_ids=tuple(row.id for row in box_rows),
        )


@pytest_asyncio.fixture
async def location_tree(
    session_factory: async_sessionmaker[AsyncSession],
) -> LocationTree:
    return await create_location_tree(session_factory)
