from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.exc import StaleDataError

from judicial_archive.core.enums import (
    CustodyStatus,
    LocationHistorySource,
    MovementStatus,
    MovementType,
    TransferMode,
)
from judicial_archive.core.errors import (
    ConflictError,
    ForbiddenError,
    InvalidParameterError,
    NotFoundError,
)
from judicial_archive.core.pagination import Page, PageParams
from judicial_archive.core.text import clean_optional_text
from judicial_archive.modules.audit.services import record_audit_event
from judicial_archive.modules.boxes.models import Box, BoxLocationHistory, BoxMovement
from judicial_archive.modules.boxes.repositories import BoxRepository
from judicial_archive.modules.boxes.schemas import (
    BoxLocationHistoryOut,
    BoxSummaryOut,
)
from judicial_archive.modules.locations import schemas as location_schemas
from judicial_archive.modules.locations.models import Area, Position, Shelf, Tray
from judicial_archive.modules.locations.occupancy import (
    classify_location_state,
    is_operable,
    precision_for,
)
from judicial_archive.modules.locations.repositories import LocationsRepository
from judicial_archive.modules.movements import schemas
from judicial_archive.modules.movements.repositories import MovementsRepository
from judicial_archive.modules.users.models import User


def _box_snapshot(box: Box, *, precision: str | None = None) -> dict[str, object]:
    return {
        "current_position_id": str(box.current_position_id) if box.current_position_id else None,
        "custody_status": box.custody_status,
        "location_precision": precision or box.location_precision,
        "version": box.version,
    }


def _movement_snapshot(movement: BoxMovement) -> dict[str, object]:
    return {
        "box_id": str(movement.box_id),
        "movement_type": movement.movement_type,
        "movement_status": movement.movement_status,
        "from_position_id": str(movement.from_position_id) if movement.from_position_id else None,
        "to_position_id": str(movement.to_position_id) if movement.to_position_id else None,
        "occurred_at": movement.occurred_at.isoformat(),
        "completed_at": movement.completed_at.isoformat() if movement.completed_at else None,
        "cancelled_at": movement.cancelled_at.isoformat() if movement.cancelled_at else None,
        "reason": movement.reason,
    }


def _history_out(history: BoxLocationHistory) -> BoxLocationHistoryOut:
    return BoxLocationHistoryOut(
        id=history.id,
        box_id=history.box_id,
        movement_id=history.movement_id,
        from_position_id=history.from_position_id,
        to_position_id=history.to_position_id,
        from_custody_status=history.from_custody_status,
        to_custody_status=history.to_custody_status,
        from_location_precision=history.from_location_precision,
        to_location_precision=history.to_location_precision,
        reason=history.reason,
        source=history.source,
        changed_at=history.changed_at,
        changed_by=history.changed_by,
        notes=history.notes,
    )


def _path_out(
    row: tuple[Position, Tray, Shelf, Area],
) -> location_schemas.PositionPathOut:
    position, tray, shelf, area = row
    return location_schemas.PositionPathOut(
        position_id=position.id,
        position_code=position.code,
        label=position.label,
        position_status=position.status,
        tray=location_schemas.TrayPathOut(
            id=tray.id,
            code=tray.code,
            name=tray.name,
        ),
        shelf=location_schemas.ShelfPathOut(
            id=shelf.id,
            code=shelf.code,
            name=shelf.name,
        ),
        area=location_schemas.AreaPathOut(
            id=area.id,
            code=area.code,
            name=area.name,
        ),
    )


def _box_summary(box: Box) -> BoxSummaryOut:
    return BoxSummaryOut(
        box_id=box.id,
        visible_number=box.visible_number,
        box_type=box.box_type,
        year=box.year,
        court_id=box.court_id,
        lifecycle_status=box.lifecycle_status,
        custody_status=box.custody_status,
        location_precision=box.location_precision,
        location_state=classify_location_state(box),
    )


async def _movement_out(
    session: AsyncSession,
    movement: BoxMovement,
) -> schemas.MovementOut:
    repo = LocationsRepository(session)
    ids = [
        position_id
        for position_id in (movement.from_position_id, movement.to_position_id)
        if position_id is not None
    ]
    paths = await repo.list_position_paths(ids)
    from_position = (
        _path_out(paths[movement.from_position_id])
        if movement.from_position_id and movement.from_position_id in paths
        else None
    )
    to_position = (
        _path_out(paths[movement.to_position_id])
        if movement.to_position_id and movement.to_position_id in paths
        else None
    )
    return schemas.MovementOut(
        id=movement.id,
        box_id=movement.box_id,
        movement_type=movement.movement_type,
        movement_status=movement.movement_status,
        from_position=from_position,
        to_position=to_position,
        occurred_at=movement.occurred_at,
        completed_at=movement.completed_at,
        cancelled_at=movement.cancelled_at,
        reason=movement.reason,
        performed_by=movement.performed_by,
        notes=movement.notes,
        version=movement.version,
    )


async def _box_location_detail(
    session: AsyncSession,
    box: Box,
) -> schemas.BoxLocationDetailOut:
    repo = LocationsRepository(session)
    movements = MovementsRepository(session)
    current_path = (
        await repo.get_position_path(box.current_position_id) if box.current_position_id else None
    )
    open_movement = await movements.get_open_for_box(box.id)
    last_movement = await movements.get_last_for_box(box.id)
    history_count = await BoxRepository(session).count_history(box.id)
    return schemas.BoxLocationDetailOut(
        box=_box_summary(box),
        current_position=_path_out(current_path) if current_path else None,
        open_movement=(await _movement_out(session, open_movement) if open_movement else None),
        last_movement=(await _movement_out(session, last_movement) if last_movement else None),
        history_count=history_count,
        operable=is_operable(box),
        version=box.version,
    )


async def _get_box_for_update(
    session: AsyncSession,
    box_id: UUID,
) -> Box:
    box = await BoxRepository(session).get_for_update(box_id)
    if box is None:
        raise NotFoundError("Caja no encontrada.")
    if box.lifecycle_status != "ACTIVE":
        raise ForbiddenError(
            "La caja no esta activa para operaciones de ubicacion.",
            details={
                "reason": "box_not_active",
                "lifecycle_status": box.lifecycle_status,
            },
        )
    return box


def _check_version(box: Box, expected_version: int) -> None:
    if box.version != expected_version:
        raise ConflictError(
            "La caja fue modificada por otra operacion; recargue y reintente.",
            details={
                "reason": "stale_version",
                "current_version": box.version,
            },
        )


async def _ensure_no_open_movement(
    session: AsyncSession,
    box_id: UUID,
) -> None:
    movement = await MovementsRepository(session).get_open_for_box(box_id)
    if movement is not None:
        raise ConflictError(
            "La caja ya tiene un movimiento abierto.",
            details={
                "reason": "open_movement_exists",
                "movement_id": str(movement.id),
            },
        )


async def _lock_positions(
    session: AsyncSession,
    *position_ids: UUID | None,
) -> dict[UUID, Position]:
    ids = [position_id for position_id in position_ids if position_id is not None]
    positions = await LocationsRepository(session).get_positions_for_update(ids)
    return {position.id: position for position in positions}


async def _validate_target_position(
    session: AsyncSession,
    position: Position,
) -> None:
    path = await LocationsRepository(session).get_position_path(position.id)
    if path is None:
        raise NotFoundError("Posicion no encontrada.")
    _, tray, shelf, area = path
    if tray.status != "ACTIVE":
        raise ConflictError(
            "La bandeja destino esta inactiva.",
            details={"reason": "tray_inactive", "tray_id": str(tray.id)},
        )
    if shelf.status != "ACTIVE":
        raise ConflictError(
            "El anaquel destino esta inactivo.",
            details={"reason": "shelf_inactive", "shelf_id": str(shelf.id)},
        )
    if area.status != "ACTIVE":
        raise ConflictError(
            "El area destino esta inactiva.",
            details={"reason": "area_inactive", "area_id": str(area.id)},
        )
    if position.status == "RETIRED":
        raise ConflictError(
            "La posicion destino esta retirada.",
            details={"reason": "position_retired", "position_id": str(position.id)},
        )
    if position.status == "BLOCKED":
        raise ConflictError(
            "La posicion destino esta bloqueada.",
            details={"reason": "position_blocked", "position_id": str(position.id)},
        )


async def _assert_position_free(
    session: AsyncSession,
    position_id: UUID,
) -> None:
    occupied = await LocationsRepository(session).get_box_at_position(position_id)
    if occupied is not None:
        raise ConflictError(
            "La posicion destino ya esta ocupada.",
            details={
                "reason": "position_occupied",
                "position_id": str(position_id),
                "box_id": str(occupied.id),
            },
        )


def _new_movement(
    *,
    box_id: UUID,
    movement_type: str,
    movement_status: str,
    from_position_id: UUID | None,
    to_position_id: UUID | None,
    reason: str,
    actor: User,
    notes: str | None,
) -> BoxMovement:
    now = datetime.now(UTC)
    return BoxMovement(
        box_id=box_id,
        movement_type=movement_type,
        movement_status=movement_status,
        from_position_id=from_position_id,
        to_position_id=to_position_id,
        occurred_at=now,
        completed_at=now if movement_status == MovementStatus.COMPLETED.value else None,
        cancelled_at=None,
        reason=reason,
        performed_by=actor.id,
        notes=notes,
    )


async def _add_history(
    session: AsyncSession,
    *,
    box: Box,
    movement_id: UUID | None,
    from_position_id: UUID | None,
    from_custody_status: str | None,
    from_location_precision: str | None,
    to_position_id: UUID | None,
    to_custody_status: str,
    reason: str,
    actor: User,
    notes: str | None,
    source: str = LocationHistorySource.API.value,
) -> BoxLocationHistory:
    history = BoxLocationHistory(
        box_id=box.id,
        movement_id=movement_id,
        from_position_id=from_position_id,
        to_position_id=to_position_id,
        from_custody_status=from_custody_status,
        to_custody_status=to_custody_status,
        from_location_precision=from_location_precision,
        to_location_precision=precision_for(to_custody_status, to_position_id),
        reason=reason,
        source=source,
        changed_at=datetime.now(UTC),
        changed_by=actor.id,
        notes=notes,
    )
    session.add(history)
    await session.flush()
    return history


def _apply_location(
    box: Box,
    *,
    position_id: UUID | None,
    custody_status: str,
) -> None:
    box.current_position_id = position_id
    box.custody_status = custody_status


async def _commit_or_conflict(session: AsyncSession) -> None:
    try:
        await session.commit()
    except StaleDataError as exc:
        await session.rollback()
        raise ConflictError(
            "La operacion compitio con otra modificacion; recargue y reintente.",
            details={"reason": "stale_version"},
        ) from exc
    except IntegrityError as exc:
        await session.rollback()
        constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
        if constraint == "uq_boxes_current_position_occupied":
            raise ConflictError(
                "La posicion destino ya esta ocupada.",
                details={"reason": "position_occupied"},
            ) from exc
        if constraint == "uq_box_movements_open_box":
            raise ConflictError(
                "La caja ya tiene un movimiento abierto.",
                details={"reason": "open_movement_exists"},
            ) from exc
        if constraint == "ck_boxes_custody_position":
            raise ConflictError(
                "La transicion de custodia no es valida.",
                details={"reason": "invalid_transition"},
            ) from exc
        raise


async def assign_box(
    request: Request | None,
    session: AsyncSession,
    actor: User,
    box_id: UUID,
    body: schemas.AssignRequest,
) -> schemas.LocationMutationOut:
    box = await _get_box_for_update(session, box_id)
    _check_version(box, body.expected_version)
    if box.current_position_id is not None:
        raise ConflictError(
            "La caja ya tiene una posicion; use un traslado.",
            details={"reason": "box_already_located"},
        )
    if box.custody_status not in {
        CustodyStatus.UNKNOWN.value,
        CustodyStatus.MISSING.value,
    }:
        raise ConflictError(
            "La caja no puede asignarse desde su estado actual.",
            details={
                "reason": "invalid_transition",
                "custody_status": box.custody_status,
            },
        )
    await _ensure_no_open_movement(session, box.id)

    positions = await _lock_positions(session, body.position_id)
    target = positions.get(body.position_id)
    if target is None:
        raise NotFoundError("Posicion no encontrada.")
    await _validate_target_position(session, target)
    await _assert_position_free(session, target.id)

    custody = (
        CustodyStatus.IN_PLACE.value if body.confirmed else CustodyStatus.PENDING_VERIFICATION.value
    )
    before = _box_snapshot(box)
    from_custody = box.custody_status
    from_precision = box.location_precision
    movement = _new_movement(
        box_id=box.id,
        movement_type=MovementType.ASSIGN.value,
        movement_status=MovementStatus.COMPLETED.value,
        from_position_id=None,
        to_position_id=target.id,
        reason=body.reason.strip(),
        actor=actor,
        notes=clean_optional_text(body.notes, max_length=1000),
    )
    session.add(movement)
    await session.flush()

    _apply_location(box, position_id=target.id, custody_status=custody)
    history = await _add_history(
        session,
        box=box,
        movement_id=movement.id,
        from_position_id=None,
        from_custody_status=from_custody,
        from_location_precision=from_precision,
        to_position_id=target.id,
        to_custody_status=custody,
        reason=body.reason.strip(),
        actor=actor,
        notes=clean_optional_text(body.notes, max_length=1000),
    )
    after = _box_snapshot(
        box,
        precision=precision_for(custody, target.id),
    )
    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="box.location_assigned",
        entity_type="box",
        entity_id=box.id,
        before=before,
        after=after,
        metadata={
            "movement_id": str(movement.id),
            "history_id": str(history.id),
            "position_id": str(target.id),
            "confirmed": body.confirmed,
        },
    )
    await _commit_or_conflict(session)
    await session.refresh(box)
    await session.refresh(movement)
    return schemas.LocationMutationOut(
        box=await _box_location_detail(session, box),
        movement=await _movement_out(session, movement),
        history=_history_out(history),
    )


async def unassign_box(
    request: Request | None,
    session: AsyncSession,
    actor: User,
    box_id: UUID,
    body: schemas.UnassignRequest,
) -> schemas.LocationMutationOut:
    box = await _get_box_for_update(session, box_id)
    _check_version(box, body.expected_version)
    if box.current_position_id is None:
        raise ConflictError(
            "La caja no tiene ubicacion para retirar.",
            details={"reason": "box_without_location"},
        )
    if box.custody_status not in {
        CustodyStatus.IN_PLACE.value,
        CustodyStatus.PENDING_VERIFICATION.value,
    }:
        raise ConflictError(
            "La caja no puede desasignarse desde su estado actual.",
            details={
                "reason": "invalid_transition",
                "custody_status": box.custody_status,
            },
        )
    await _ensure_no_open_movement(session, box.id)

    from_position_id = box.current_position_id
    from_custody = box.custody_status
    from_precision = box.location_precision
    await _lock_positions(session, from_position_id)

    before = _box_snapshot(box)
    movement = _new_movement(
        box_id=box.id,
        movement_type=MovementType.UNASSIGN.value,
        movement_status=MovementStatus.COMPLETED.value,
        from_position_id=from_position_id,
        to_position_id=None,
        reason=body.reason.strip(),
        actor=actor,
        notes=clean_optional_text(body.notes, max_length=1000),
    )
    session.add(movement)
    await session.flush()

    _apply_location(box, position_id=None, custody_status=CustodyStatus.UNKNOWN.value)
    history = await _add_history(
        session,
        box=box,
        movement_id=movement.id,
        from_position_id=from_position_id,
        from_custody_status=from_custody,
        from_location_precision=from_precision,
        to_position_id=None,
        to_custody_status=CustodyStatus.UNKNOWN.value,
        reason=body.reason.strip(),
        actor=actor,
        notes=clean_optional_text(body.notes, max_length=1000),
    )
    after = _box_snapshot(box, precision="UNKNOWN")
    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="box.location_unassigned",
        entity_type="box",
        entity_id=box.id,
        before=before,
        after=after,
        metadata={
            "movement_id": str(movement.id),
            "history_id": str(history.id),
            "from_position_id": str(from_position_id),
        },
    )
    await _commit_or_conflict(session)
    await session.refresh(box)
    await session.refresh(movement)
    return schemas.LocationMutationOut(
        box=await _box_location_detail(session, box),
        movement=await _movement_out(session, movement),
        history=_history_out(history),
    )


async def transfer_box(
    request: Request | None,
    session: AsyncSession,
    actor: User,
    box_id: UUID,
    body: schemas.TransferRequest,
) -> schemas.LocationMutationOut:
    box = await _get_box_for_update(session, box_id)
    _check_version(box, body.expected_version)
    if box.current_position_id is None:
        raise ConflictError(
            "La caja no tiene ubicacion de origen.",
            details={"reason": "box_without_location"},
        )
    if box.custody_status not in {
        CustodyStatus.IN_PLACE.value,
        CustodyStatus.PENDING_VERIFICATION.value,
    }:
        raise ConflictError(
            "La caja no puede trasladarse desde su estado actual.",
            details={
                "reason": "invalid_transition",
                "custody_status": box.custody_status,
            },
        )
    if body.to_position_id == box.current_position_id:
        raise InvalidParameterError("La posicion destino debe ser distinta de la posicion actual.")
    await _ensure_no_open_movement(session, box.id)

    from_position_id = box.current_position_id
    from_custody = box.custody_status
    from_precision = box.location_precision
    positions = await _lock_positions(session, from_position_id, body.to_position_id)
    target = positions.get(body.to_position_id)
    if target is None:
        raise NotFoundError("Posicion destino no encontrada.")
    await _validate_target_position(session, target)
    await _assert_position_free(session, target.id)

    before = _box_snapshot(box)
    if body.mode == TransferMode.IN_TRANSIT:
        movement = _new_movement(
            box_id=box.id,
            movement_type=MovementType.TRANSFER.value,
            movement_status=MovementStatus.IN_TRANSIT.value,
            from_position_id=from_position_id,
            to_position_id=target.id,
            reason=body.reason.strip(),
            actor=actor,
            notes=clean_optional_text(body.notes, max_length=1000),
        )
        session.add(movement)
        await session.flush()
        _apply_location(
            box,
            position_id=None,
            custody_status=CustodyStatus.IN_TRANSIT.value,
        )
        history = await _add_history(
            session,
            box=box,
            movement_id=movement.id,
            from_position_id=from_position_id,
            from_custody_status=from_custody,
            from_location_precision=from_precision,
            to_position_id=None,
            to_custody_status=CustodyStatus.IN_TRANSIT.value,
            reason=body.reason.strip(),
            actor=actor,
            notes=clean_optional_text(body.notes, max_length=1000),
        )
        after = _box_snapshot(box, precision="UNKNOWN")
    else:
        custody = (
            CustodyStatus.IN_PLACE.value
            if body.confirmed
            else CustodyStatus.PENDING_VERIFICATION.value
        )
        movement = _new_movement(
            box_id=box.id,
            movement_type=MovementType.TRANSFER.value,
            movement_status=MovementStatus.COMPLETED.value,
            from_position_id=from_position_id,
            to_position_id=target.id,
            reason=body.reason.strip(),
            actor=actor,
            notes=clean_optional_text(body.notes, max_length=1000),
        )
        session.add(movement)
        await session.flush()
        _apply_location(box, position_id=target.id, custody_status=custody)
        history = await _add_history(
            session,
            box=box,
            movement_id=movement.id,
            from_position_id=from_position_id,
            from_custody_status=from_custody,
            from_location_precision=from_precision,
            to_position_id=target.id,
            to_custody_status=custody,
            reason=body.reason.strip(),
            actor=actor,
            notes=clean_optional_text(body.notes, max_length=1000),
        )
        after = _box_snapshot(box, precision=precision_for(custody, target.id))

    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="box.location_transferred",
        entity_type="box",
        entity_id=box.id,
        before=before,
        after=after,
        metadata={
            "movement_id": str(movement.id),
            "history_id": str(history.id),
            "from_position_id": str(from_position_id),
            "to_position_id": str(target.id),
            "mode": body.mode.value,
            "confirmed": body.confirmed,
        },
    )
    await _commit_or_conflict(session)
    await session.refresh(box)
    await session.refresh(movement)
    return schemas.LocationMutationOut(
        box=await _box_location_detail(session, box),
        movement=await _movement_out(session, movement),
        history=_history_out(history),
    )


async def confirm_location(
    request: Request | None,
    session: AsyncSession,
    actor: User,
    box_id: UUID,
    body: schemas.ConfirmRequest,
) -> schemas.LocationMutationOut:
    box = await _get_box_for_update(session, box_id)
    _check_version(box, body.expected_version)
    if box.current_position_id is None:
        raise ConflictError(
            "La caja no tiene posicion para confirmar.",
            details={"reason": "box_without_location"},
        )
    if box.custody_status != CustodyStatus.PENDING_VERIFICATION.value:
        raise ConflictError(
            "La caja no esta pendiente de confirmacion.",
            details={
                "reason": "invalid_transition",
                "custody_status": box.custody_status,
            },
        )
    position_id = box.current_position_id
    positions = await _lock_positions(session, position_id)
    if position_id not in positions:
        raise NotFoundError("Posicion no encontrada.")

    before = _box_snapshot(box)
    _apply_location(
        box,
        position_id=position_id,
        custody_status=CustodyStatus.IN_PLACE.value,
    )
    history = await _add_history(
        session,
        box=box,
        movement_id=None,
        from_position_id=position_id,
        from_custody_status=CustodyStatus.PENDING_VERIFICATION.value,
        from_location_precision="PENDING",
        to_position_id=position_id,
        to_custody_status=CustodyStatus.IN_PLACE.value,
        reason=body.reason.strip(),
        actor=actor,
        notes=clean_optional_text(body.notes, max_length=1000),
    )
    after = _box_snapshot(box, precision="CONFIRMED")
    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="box.location_confirmed",
        entity_type="box",
        entity_id=box.id,
        before=before,
        after=after,
        metadata={
            "history_id": str(history.id),
            "position_id": str(position_id),
        },
    )
    await _commit_or_conflict(session)
    await session.refresh(box)
    return schemas.LocationMutationOut(
        box=await _box_location_detail(session, box),
        movement=None,
        history=_history_out(history),
    )


async def complete_movement(
    request: Request | None,
    session: AsyncSession,
    actor: User,
    movement_id: UUID,
    body: schemas.CompleteMovementRequest,
) -> schemas.LocationMutationOut:
    movement = await MovementsRepository(session).get_for_update(movement_id)
    if movement is None:
        raise NotFoundError("Movimiento no encontrado.")
    if movement.movement_type != MovementType.TRANSFER.value:
        raise ConflictError(
            "Solo los traslados pueden completarse en B6.",
            details={"reason": "unsupported_movement_type"},
        )
    if movement.movement_status != MovementStatus.IN_TRANSIT.value:
        raise ConflictError(
            "El movimiento no esta en transito.",
            details={
                "reason": "movement_not_in_transit",
                "movement_status": movement.movement_status,
            },
        )

    box = await _get_box_for_update(session, movement.box_id)
    _check_version(box, body.expected_version)
    if box.custody_status != CustodyStatus.IN_TRANSIT.value:
        raise ConflictError(
            "La caja no esta en transito.",
            details={
                "reason": "invalid_transition",
                "custody_status": box.custody_status,
            },
        )
    if movement.to_position_id is None:
        raise ConflictError(
            "El movimiento no tiene posicion destino.",
            details={"reason": "movement_without_target"},
        )

    positions = await _lock_positions(session, movement.to_position_id)
    target = positions.get(movement.to_position_id)
    if target is None:
        raise NotFoundError("Posicion destino no encontrada.")
    await _validate_target_position(session, target)
    await _assert_position_free(session, target.id)

    custody = (
        CustodyStatus.IN_PLACE.value if body.confirmed else CustodyStatus.PENDING_VERIFICATION.value
    )
    before = _box_snapshot(box)
    before_movement = _movement_snapshot(movement)
    movement.movement_status = MovementStatus.COMPLETED.value
    movement.completed_at = datetime.now(UTC)
    _apply_location(box, position_id=target.id, custody_status=custody)
    history = await _add_history(
        session,
        box=box,
        movement_id=movement.id,
        from_position_id=None,
        from_custody_status=CustodyStatus.IN_TRANSIT.value,
        from_location_precision="UNKNOWN",
        to_position_id=target.id,
        to_custody_status=custody,
        reason=body.reason.strip(),
        actor=actor,
        notes=clean_optional_text(body.notes, max_length=1000),
    )
    after = _box_snapshot(box, precision=precision_for(custody, target.id))
    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="box.location_transfer_completed",
        entity_type="box",
        entity_id=box.id,
        before=before,
        after=after,
        metadata={
            "movement_id": str(movement.id),
            "movement_before": before_movement,
            "history_id": str(history.id),
            "to_position_id": str(target.id),
            "confirmed": body.confirmed,
        },
    )
    await _commit_or_conflict(session)
    await session.refresh(box)
    await session.refresh(movement)
    return schemas.LocationMutationOut(
        box=await _box_location_detail(session, box),
        movement=await _movement_out(session, movement),
        history=_history_out(history),
    )


async def cancel_movement(
    request: Request | None,
    session: AsyncSession,
    actor: User,
    movement_id: UUID,
    body: schemas.CancelMovementRequest,
) -> schemas.LocationMutationOut:
    movement = await MovementsRepository(session).get_for_update(movement_id)
    if movement is None:
        raise NotFoundError("Movimiento no encontrado.")
    if movement.movement_type != MovementType.TRANSFER.value:
        raise ConflictError(
            "Solo los traslados pueden cancelarse en B6.",
            details={"reason": "unsupported_movement_type"},
        )
    if movement.movement_status != MovementStatus.IN_TRANSIT.value:
        raise ConflictError(
            "El movimiento no esta en transito.",
            details={
                "reason": "movement_not_in_transit",
                "movement_status": movement.movement_status,
            },
        )

    box = await _get_box_for_update(session, movement.box_id)
    _check_version(box, body.expected_version)
    if box.custody_status != CustodyStatus.IN_TRANSIT.value:
        raise ConflictError(
            "La caja no esta en transito.",
            details={
                "reason": "invalid_transition",
                "custody_status": box.custody_status,
            },
        )

    history_origin = await BoxRepository(session).get_last_history_for_movement(movement.id)
    if history_origin is None:
        raise ConflictError(
            "No existe historial de origen para restaurar el traslado.",
            details={"reason": "movement_without_origin_history"},
        )

    origin_position_id = history_origin.from_position_id
    origin_custody = history_origin.from_custody_status or CustodyStatus.UNKNOWN.value
    origin_precision = history_origin.from_location_precision or "UNKNOWN"
    if origin_position_id is not None:
        positions = await _lock_positions(session, origin_position_id)
        origin = positions.get(origin_position_id)
        if origin is None:
            raise NotFoundError("Posicion de origen no encontrada.")
        occupied = await LocationsRepository(session).get_box_at_position(origin_position_id)
        if occupied is not None and occupied.id != box.id:
            raise ConflictError(
                "La posicion de origen fue ocupada durante el transito.",
                details={
                    "reason": "origin_occupied",
                    "position_id": str(origin_position_id),
                    "box_id": str(occupied.id),
                },
            )
        if origin.status != "AVAILABLE":
            raise ConflictError(
                "La posicion de origen no esta disponible.",
                details={
                    "reason": "origin_unavailable",
                    "position_id": str(origin_position_id),
                    "position_status": origin.status,
                },
            )

    before = _box_snapshot(box)
    before_movement = _movement_snapshot(movement)
    movement.movement_status = MovementStatus.CANCELLED.value
    movement.cancelled_at = datetime.now(UTC)

    if origin_position_id is not None:
        _apply_location(
            box,
            position_id=origin_position_id,
            custody_status=origin_custody,
        )
        history = await _add_history(
            session,
            box=box,
            movement_id=movement.id,
            from_position_id=None,
            from_custody_status=CustodyStatus.IN_TRANSIT.value,
            from_location_precision="UNKNOWN",
            to_position_id=origin_position_id,
            to_custody_status=origin_custody,
            reason=body.reason.strip(),
            actor=actor,
            notes=clean_optional_text(body.notes, max_length=1000),
        )
        after = _box_snapshot(box, precision=origin_precision)
    else:
        _apply_location(
            box,
            position_id=None,
            custody_status=CustodyStatus.UNKNOWN.value,
        )
        history = await _add_history(
            session,
            box=box,
            movement_id=movement.id,
            from_position_id=None,
            from_custody_status=CustodyStatus.IN_TRANSIT.value,
            from_location_precision="UNKNOWN",
            to_position_id=None,
            to_custody_status=CustodyStatus.UNKNOWN.value,
            reason=body.reason.strip(),
            actor=actor,
            notes=clean_optional_text(body.notes, max_length=1000),
        )
        after = _box_snapshot(box, precision="UNKNOWN")

    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="box.location_transfer_cancelled",
        entity_type="box",
        entity_id=box.id,
        before=before,
        after=after,
        metadata={
            "movement_id": str(movement.id),
            "movement_before": before_movement,
            "history_id": str(history.id),
            "restored_position_id": str(origin_position_id) if origin_position_id else None,
        },
    )
    await _commit_or_conflict(session)
    await session.refresh(box)
    await session.refresh(movement)
    return schemas.LocationMutationOut(
        box=await _box_location_detail(session, box),
        movement=await _movement_out(session, movement),
        history=_history_out(history),
    )


async def get_box_location(
    session: AsyncSession,
    box_id: UUID,
) -> schemas.BoxLocationDetailOut:
    box = await BoxRepository(session).get(box_id)
    if box is None:
        raise NotFoundError("Caja no encontrada.")
    return await _box_location_detail(session, box)


async def list_box_history(
    session: AsyncSession,
    *,
    params: PageParams,
    box_id: UUID,
    from_date: datetime | None,
    to_date: datetime | None,
    source: str | None,
) -> Page[BoxLocationHistoryOut]:
    box = await BoxRepository(session).get(box_id)
    if box is None:
        raise NotFoundError("Caja no encontrada.")
    rows, total = await BoxRepository(session).list_history(
        box_id,
        from_date=from_date,
        to_date=to_date,
        source=source,
        offset=params.offset,
        limit=params.limit,
    )
    items = [_history_out(row) for row in rows]
    return Page[BoxLocationHistoryOut].build(items, total=total, params=params)


async def list_movements(
    session: AsyncSession,
    *,
    params: PageParams,
    box_id: UUID | None,
    movement_type: str | None,
    movement_status: str | None,
    from_date: datetime | None,
    to_date: datetime | None,
) -> Page[schemas.MovementOut]:
    rows, total = await MovementsRepository(session).list(
        box_id=box_id,
        movement_type=movement_type,
        movement_status=movement_status,
        from_date=from_date,
        to_date=to_date,
        offset=params.offset,
        limit=params.limit,
    )
    items = [await _movement_out(session, row) for row in rows]
    return Page[schemas.MovementOut].build(items, total=total, params=params)


async def get_movement(
    session: AsyncSession,
    movement_id: UUID,
) -> schemas.MovementOut:
    movement = await MovementsRepository(session).get(movement_id)
    if movement is None:
        raise NotFoundError("Movimiento no encontrado.")
    return await _movement_out(session, movement)
