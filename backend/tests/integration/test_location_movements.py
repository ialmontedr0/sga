from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import select

from judicial_archive.core.enums import CustodyStatus, MovementStatus
from judicial_archive.core.errors import ConflictError
from judicial_archive.modules.boxes.models import Box
from judicial_archive.modules.movements import services
from judicial_archive.modules.movements.schemas import (
    AssignRequest,
    CancelMovementRequest,
    CompleteMovementRequest,
    TransferRequest,
)
from judicial_archive.modules.users.models import User
from tests.integration.auth_helpers import ADMIN_USERNAME, seed_admin
from tests.integration.location_fixtures import NO_REQUEST, create_location_tree

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture(autouse=True)
async def _seeded_admin(session_factory) -> None:
    await seed_admin(session_factory)


async def _actor(session):
    user = await session.scalar(select(User).where(User.username == ADMIN_USERNAME))
    assert user is not None
    return user


async def test_assign_creates_history_and_movement(db_session, session_factory) -> None:
    tree = await create_location_tree(session_factory)
    actor = await _actor(db_session)
    box = await db_session.get(Box, tree.box_ids[0])

    result = await services.assign_box(
        NO_REQUEST,
        db_session,
        actor,
        box.id,
        AssignRequest(
            position_id=tree.position_ids[0],
            confirmed=True,
            reason="Asignacion inicial",
            expected_version=box.version,
        ),
    )

    assert result.box.box.custody_status == CustodyStatus.IN_PLACE.value
    assert result.box.current_position is not None
    assert result.movement is not None
    assert result.movement.movement_type == "ASSIGN"
    assert result.history.to_position_id == tree.position_ids[0]
    assert result.history.from_custody_status == CustodyStatus.UNKNOWN.value


async def test_assign_requires_pending_verification_when_not_confirmed(
    db_session,
    session_factory,
) -> None:
    tree = await create_location_tree(session_factory)
    actor = await _actor(db_session)
    box = await db_session.get(Box, tree.box_ids[0])

    result = await services.assign_box(
        NO_REQUEST,
        db_session,
        actor,
        box.id,
        AssignRequest(
            position_id=tree.position_ids[0],
            confirmed=False,
            reason="Ubicacion sin verificar",
            expected_version=box.version,
        ),
    )

    assert result.box.box.custody_status == CustodyStatus.PENDING_VERIFICATION.value
    assert result.box.box.location_state == "PENDING_CONFIRMATION"


async def test_assign_rejects_occupied_position(db_session, session_factory) -> None:
    tree = await create_location_tree(session_factory)
    actor = await _actor(db_session)
    first = await db_session.get(Box, tree.box_ids[0])
    second = await db_session.get(Box, tree.box_ids[1])

    await services.assign_box(
        NO_REQUEST,
        db_session,
        actor,
        first.id,
        AssignRequest(
            position_id=tree.position_ids[0],
            confirmed=True,
            reason="Primera caja",
            expected_version=first.version,
        ),
    )
    second = await db_session.get(Box, second.id)

    with pytest.raises(ConflictError) as exc:
        await services.assign_box(
            NO_REQUEST,
            db_session,
            actor,
            second.id,
            AssignRequest(
                position_id=tree.position_ids[0],
                confirmed=True,
                reason="Segunda caja",
                expected_version=second.version,
            ),
        )

    assert exc.value.details is not None
    assert exc.value.details["reason"] == "position_occupied"


async def test_transfer_immediate_updates_location(db_session, session_factory) -> None:
    tree = await create_location_tree(session_factory)
    actor = await _actor(db_session)
    box = await db_session.get(Box, tree.box_ids[0])
    assigned = await services.assign_box(
        NO_REQUEST,
        db_session,
        actor,
        box.id,
        AssignRequest(
            position_id=tree.position_ids[0],
            confirmed=True,
            reason="Origen",
            expected_version=box.version,
        ),
    )

    result = await services.transfer_box(
        NO_REQUEST,
        db_session,
        actor,
        box.id,
        TransferRequest(
            to_position_id=tree.position_ids[1],
            mode="IMMEDIATE",  # pyright: ignore[reportArgumentType]
            confirmed=True,
            reason="Traslado directo",
            expected_version=assigned.box.version,
        ),
    )

    assert result.box.current_position is not None
    assert result.box.current_position.position_id == tree.position_ids[1]
    assert result.movement is not None
    assert result.movement.movement_type == "TRANSFER"
    assert result.movement.movement_status == MovementStatus.COMPLETED.value


async def test_transfer_in_transit_then_complete(db_session, session_factory) -> None:
    tree = await create_location_tree(session_factory)
    actor = await _actor(db_session)
    box = await db_session.get(Box, tree.box_ids[0])
    assigned = await services.assign_box(
        NO_REQUEST,
        db_session,
        actor,
        box.id,
        AssignRequest(
            position_id=tree.position_ids[0],
            confirmed=True,
            reason="Origen",
            expected_version=box.version,
        ),
    )

    in_transit = await services.transfer_box(
        NO_REQUEST,
        db_session,
        actor,
        box.id,
        TransferRequest(
            to_position_id=tree.position_ids[1],
            mode="IN_TRANSIT",  # pyright: ignore[reportArgumentType]
            confirmed=False,
            reason="Traslado en dos fases",
            expected_version=assigned.box.version,
        ),
    )
    assert in_transit.movement is not None
    assert in_transit.box.box.custody_status == CustodyStatus.IN_TRANSIT.value
    assert in_transit.box.current_position is None
    assert in_transit.box.open_movement is not None

    completed = await services.complete_movement(
        NO_REQUEST,
        db_session,
        actor,
        in_transit.movement.id,
        CompleteMovementRequest(
            confirmed=True,
            reason="Recepcion confirmada",
            expected_version=in_transit.box.version,
        ),
    )
    assert completed.box.current_position is not None
    assert completed.box.box.custody_status == CustodyStatus.IN_PLACE.value
    assert completed.box.current_position.position_id == tree.position_ids[1]


async def test_cancel_in_transit_restores_origin(db_session, session_factory) -> None:
    tree = await create_location_tree(session_factory)
    actor = await _actor(db_session)
    box = await db_session.get(Box, tree.box_ids[0])
    assigned = await services.assign_box(
        NO_REQUEST,
        db_session,
        actor,
        box.id,
        AssignRequest(
            position_id=tree.position_ids[0],
            confirmed=True,
            reason="Origen",
            expected_version=box.version,
        ),
    )

    in_transit = await services.transfer_box(
        NO_REQUEST,
        db_session,
        actor,
        box.id,
        TransferRequest(
            to_position_id=tree.position_ids[1],
            mode="IN_TRANSIT",  # pyright: ignore[reportArgumentType]
            confirmed=False,
            reason="Traslado",
            expected_version=assigned.box.version,
        ),
    )
    assert in_transit.movement is not None  # pyright: ignore[reportCallIssue]
    cancelled = await services.cancel_movement(
        NO_REQUEST,
        db_session,
        actor,
        in_transit.movement.id,
        CancelMovementRequest(
            reason="Se cancela el traslado",
            expected_version=in_transit.box.version,
        ),
    )

    assert cancelled.box.current_position is not None
    assert cancelled.box.current_position.position_id == tree.position_ids[0]
