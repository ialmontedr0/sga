from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from typing import cast
from uuid import UUID

import pytest
from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.core.errors import ConflictError, InvalidParameterError
from judicial_archive.modules.boxes.models import Box
from judicial_archive.modules.courts.models import Court
from judicial_archive.modules.locations import services
from judicial_archive.modules.locations.capacity import (
    CapacityPlan,
    apply_capacity_plan,
    build_capacity_plan,
)
from judicial_archive.modules.locations.models import Area, Position, Shelf, Tray
from judicial_archive.modules.locations.repositories import LocationsRepository
from judicial_archive.modules.locations.schemas import CapacityApplyRequest, CapacityTarget
from judicial_archive.modules.users.models import User

pytestmark = pytest.mark.integration


async def _new_shelf(session: AsyncSession, *, code: str = "Q1") -> Shelf:
    area = Area(code=f"A{code}", name=f"Zona {code}", status="ACTIVE")
    session.add(area)
    await session.flush()
    shelf = Shelf(
        area_id=area.id,
        code=code,
        name=f"Anaquel {code}",
        levels=None,
        positions_per_level=None,
        status="ACTIVE",
    )
    session.add(shelf)
    await session.flush()
    return shelf


async def _structure(
    session: AsyncSession,
    shelf_id: UUID,
) -> tuple[Shelf, Sequence[Tray], Sequence[Position]]:
    repo = LocationsRepository(session)
    shelf, trays, positions = await repo.get_shelf_structure_for_update(shelf_id)
    assert shelf is not None
    return shelf, trays, positions


def _group(positions: Sequence[Position]) -> dict[UUID, list[Position]]:
    grouped: dict[UUID, list[Position]] = defaultdict(list)
    for position in positions:
        grouped[position.tray_id].append(position)
    return grouped


async def _apply(
    session: AsyncSession,
    shelf_id: UUID,
    levels: int,
    positions_per_level: int,
) -> tuple[Shelf, CapacityPlan]:
    shelf, trays, positions = await _structure(session, shelf_id)
    repo = LocationsRepository(session)
    occupied = await repo.occupied_position_ids([position.id for position in positions])
    plan = build_capacity_plan(
        shelf_id=shelf.id,
        target_levels=levels,
        positions_per_level=positions_per_level,
        trays=trays,
        positions_by_tray=_group(positions),
        occupied_position_ids=occupied,
    )
    await apply_capacity_plan(
        session=session,
        shelf=shelf,
        plan=plan,
        trays_by_id={tray.id: tray for tray in trays},
        positions_by_id={position.id: position for position in positions},
    )
    await session.commit()
    await session.refresh(shelf)
    return shelf, plan


async def _count(session: AsyncSession, model: type[object]) -> int:
    value = await session.scalar(select(func.count()).select_from(model))
    assert value is not None
    return int(value)


async def _occupy(session: AsyncSession, position: Position) -> None:
    court = Court(
        code_raw="930",
        code_normalized="930",
        name="Tribunal de capacidad",
        status="ACTIVE",
    )
    session.add(court)
    await session.flush()
    session.add(
        Box(
            court_id=court.id,
            year=2026,
            visible_number="CAP-0001",
            current_position_id=position.id,
            custody_status="IN_PLACE",
        )
    )
    await session.flush()


@pytest.mark.asyncio
async def test_create_shelf_with_2x2_creates_trays_and_positions(
    db_session: AsyncSession,
) -> None:
    shelf = await _new_shelf(db_session)
    shelf, plan = await _apply(db_session, shelf.id, 2, 2)

    assert plan.trays_to_create == 2
    assert plan.positions_to_create == 4
    assert await _count(db_session, Tray) == 2
    assert await _count(db_session, Position) == 4
    assert shelf.capacity_positions == 4
    assert shelf.levels == 2
    assert shelf.positions_per_level == 2


@pytest.mark.asyncio
async def test_apply_2x3_creates_two_positions_and_increments_version(
    db_session: AsyncSession,
) -> None:
    shelf = await _new_shelf(db_session)
    shelf, _ = await _apply(db_session, shelf.id, 2, 2)
    old_version = shelf.version

    shelf, plan = await _apply(db_session, shelf.id, 2, 3)

    assert plan.positions_to_create == 2
    assert await _count(db_session, Position) == 6
    assert shelf.capacity_positions == 6
    assert shelf.version > old_version


@pytest.mark.asyncio
async def test_reduce_capacity_with_occupied_excess_conflicts(
    db_session: AsyncSession,
) -> None:
    shelf = await _new_shelf(db_session)
    await _apply(db_session, shelf.id, 2, 3)
    shelf, _, positions = await _structure(db_session, shelf.id)
    occupied = sorted(positions, key=lambda item: (item.tray_id, item.code))[2]
    await _occupy(db_session, occupied)

    with pytest.raises(ConflictError):
        await services.apply_capacity(
            cast(Request, None),
            db_session,
            cast(User, None),
            shelf.id,
            CapacityApplyRequest(
                levels=2,
                positions_per_level=2,
                expected_version=shelf.version,
            ),
        )


@pytest.mark.asyncio
async def test_reduce_capacity_with_blocked_excess_conflicts(
    db_session: AsyncSession,
) -> None:
    shelf = await _new_shelf(db_session)
    await _apply(db_session, shelf.id, 2, 3)
    shelf, _, positions = await _structure(db_session, shelf.id)
    blocked = sorted(positions, key=lambda item: (item.tray_id, item.code))[2]
    blocked.status = "BLOCKED"
    await db_session.commit()

    with pytest.raises(ConflictError):
        await services.apply_capacity(
            cast(Request, None),
            db_session,
            cast(User, None),
            shelf.id,
            CapacityApplyRequest(
                levels=2,
                positions_per_level=2,
                expected_version=shelf.version,
            ),
        )


@pytest.mark.asyncio
async def test_capacity_above_5000_is_rejected(db_session: AsyncSession) -> None:
    shelf = await _new_shelf(db_session)
    with pytest.raises(InvalidParameterError):
        build_capacity_plan(
            shelf_id=shelf.id,
            target_levels=5001,
            positions_per_level=1,
            trays=[],
            positions_by_tray={},
            occupied_position_ids=set(),
        )


@pytest.mark.asyncio
async def test_reduction_retires_without_deleting_rows(db_session: AsyncSession) -> None:
    shelf = await _new_shelf(db_session)
    await _apply(db_session, shelf.id, 2, 3)
    shelf, plan = await _apply(db_session, shelf.id, 2, 2)

    assert plan.positions_to_retire == 2
    assert await _count(db_session, Position) == 6
    retired = await db_session.scalar(
        select(func.count()).select_from(Position).where(Position.status == "RETIRED")
    )
    assert retired == 2
    assert shelf.capacity_positions == 4


@pytest.mark.asyncio
async def test_preview_does_not_modify_data(db_session: AsyncSession) -> None:
    shelf = await _new_shelf(db_session)
    await _apply(db_session, shelf.id, 2, 2)
    before_trays = await _count(db_session, Tray)
    before_positions = await _count(db_session, Position)

    plan = await services.preview_capacity(
        db_session,
        shelf.id,
        CapacityTarget(levels=2, positions_per_level=3),
    )

    assert plan.positions_to_create == 2
    assert await _count(db_session, Tray) == before_trays
    assert await _count(db_session, Position) == before_positions
