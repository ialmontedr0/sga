from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import select

from judicial_archive.core.pagination import PageParams
from judicial_archive.modules.boxes.models import Box
from judicial_archive.modules.locations import services
from judicial_archive.modules.movements import services as movement_services
from judicial_archive.modules.movements.schemas import AssignRequest
from judicial_archive.modules.users.models import User
from tests.integration.auth_helpers import ADMIN_USERNAME, seed_admin
from tests.integration.location_fixtures import NO_REQUEST, create_location_tree

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture(autouse=True)
async def _seeded_admin(session_factory) -> None:
    await seed_admin(session_factory)


async def test_scan_unknown_box_is_unregistered(db_session) -> None:
    result = await services.scan(
        db_session,
        box_number="NO-EXISTE",
        position_id=None,
    )

    assert result.kind == "UNREGISTERED_BOX"
    assert result.operable is False


async def test_scan_position_before_and_after_assignment(db_session, session_factory) -> None:
    tree = await create_location_tree(session_factory)

    empty = await services.scan(
        db_session,
        box_number=None,
        position_id=tree.position_ids[0],
    )
    assert empty.kind == "POSITION"
    assert empty.position_state == "EMPTY"

    actor = await db_session.scalar(select(User).where(User.username == ADMIN_USERNAME))
    assert actor is not None
    box = await db_session.get(Box, tree.box_ids[0])
    await movement_services.assign_box(
        NO_REQUEST,
        db_session,
        actor,
        box.id,
        AssignRequest(
            position_id=tree.position_ids[0],
            confirmed=True,
            reason="Escanear posicion",
            expected_version=box.version,
        ),
    )

    occupied = await services.scan(
        db_session,
        box_number=None,
        position_id=tree.position_ids[0],
    )
    assert occupied.position_state == "OCCUPIED"
    assert occupied.box is not None
    assert occupied.box.box_id == tree.box_ids[0]


async def test_scan_box_returns_location_state(db_session, session_factory) -> None:
    tree = await create_location_tree(session_factory)
    actor = await db_session.scalar(select(User).where(User.username == ADMIN_USERNAME))
    assert actor is not None
    box = await db_session.get(Box, tree.box_ids[0])
    await movement_services.assign_box(
        NO_REQUEST,
        db_session,
        actor,
        box.id,
        AssignRequest(
            position_id=tree.position_ids[0],
            confirmed=True,
            reason="Escanear caja",
            expected_version=box.version,
        ),
    )

    result = await services.scan(
        db_session,
        box_number=box.visible_number,
        position_id=None,
    )

    assert result.kind == "BOX"
    assert result.location_state == "CONFIRMED"
    assert result.current_position is not None
    assert result.current_position.position_id == tree.position_ids[0]


async def test_unlocated_boxes_lists_boxes_without_position(
    db_session,
    session_factory,
) -> None:
    tree = await create_location_tree(session_factory)

    page = await services.list_unlocated_boxes(
        db_session,
        params=PageParams(),
        state="UNASSIGNED",
        q=None,
    )

    returned_ids = {item.box.box_id for item in page.items}
    assert set(tree.box_ids) <= returned_ids
    assert all(item.location_state == "UNASSIGNED" for item in page.items)
