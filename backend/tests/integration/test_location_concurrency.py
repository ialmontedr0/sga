from __future__ import annotations

import asyncio

import pytest
import pytest_asyncio
from sqlalchemy import select

from judicial_archive.core.errors import ConflictError
from judicial_archive.modules.boxes.models import Box
from judicial_archive.modules.movements import services
from judicial_archive.modules.movements.schemas import AssignRequest
from judicial_archive.modules.users.models import User
from tests.integration.auth_helpers import ADMIN_USERNAME, seed_admin
from tests.integration.location_fixtures import NO_REQUEST, create_location_tree

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture(autouse=True)
async def _seeded_admin(session_factory) -> None:
    await seed_admin(session_factory)


async def _assign_once(session_factory, box_id, position_id):
    async with session_factory() as session:
        actor = await session.scalar(select(User).where(User.username == ADMIN_USERNAME))
        assert actor is not None
        box = await session.get(Box, box_id)
        assert box is not None
        return await services.assign_box(
            NO_REQUEST,
            session,
            actor,
            box.id,
            AssignRequest(
                position_id=position_id,
                confirmed=True,
                reason="Concurrencia",
                expected_version=box.version,
            ),
        )


async def test_two_assignments_only_one_wins(session_factory) -> None:
    tree = await create_location_tree(session_factory)

    results = await asyncio.gather(
        _assign_once(session_factory, tree.box_ids[0], tree.position_ids[0]),
        _assign_once(session_factory, tree.box_ids[1], tree.position_ids[0]),
        return_exceptions=True,
    )

    successes = [item for item in results if not isinstance(item, Exception)]
    conflicts = [item for item in results if isinstance(item, ConflictError)]

    assert len(successes) == 1
    assert len(conflicts) == 1
    assert conflicts[0].details is not None
    assert conflicts[0].details["reason"] in {
        "position_occupied",
        "stale_version",
        "open_movement_exists",
    }
