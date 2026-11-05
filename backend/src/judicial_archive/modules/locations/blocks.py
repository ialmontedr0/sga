from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.core.errors import ConflictError, InvalidParameterError, NotFoundError
from judicial_archive.core.pagination import Page, PageParams
from judicial_archive.core.text import clean_optional_text
from judicial_archive.modules.audit.services import record_audit_event
from judicial_archive.modules.locations import schemas
from judicial_archive.modules.locations.models import Area, Position, PositionBlock, Shelf, Tray
from judicial_archive.modules.locations.repositories import LocationsRepository
from judicial_archive.modules.users.models import User


def _block_snapshot(block: PositionBlock) -> dict[str, object]:
    return {
        "shelf_id": str(block.shelf_id),
        "start_position_id": str(block.start_position_id),
        "end_position_id": str(block.end_position_id),
        "first_position_number": block.first_position_number,
        "last_position_number": block.last_position_number,
        "reason": block.reason,
        "cancelled_at": block.cancelled_at.isoformat() if block.cancelled_at else None,
        "cancellation_reason": block.cancellation_reason,
    }


def _path_out(
    row: tuple[Position, Tray, Shelf, Area],
) -> schemas.PositionPathOut:
    position, tray, shelf, area = row
    return schemas.PositionPathOut(
        position_id=position.id,
        position_code=position.code,
        label=position.label,
        position_status=position.status,
        tray=schemas.TrayPathOut(id=tray.id, code=tray.code, name=tray.name),
        shelf=schemas.ShelfPathOut(id=shelf.id, code=shelf.code, name=shelf.name),
        area=schemas.AreaPathOut(id=area.id, code=area.code, name=area.name),
    )


def _sorted_positions(
    trays: Sequence[Tray],
    positions: Sequence[Position],
) -> list[Position]:
    tray_codes = {tray.id: tray.code for tray in trays}
    return sorted(
        positions,
        key=lambda position: (tray_codes[position.tray_id], position.code, str(position.id)),
    )


async def _block_out(
    session: AsyncSession,
    block: PositionBlock,
) -> schemas.PositionBlockOut:
    paths = await LocationsRepository(session).list_position_paths(
        [block.start_position_id, block.end_position_id]
    )
    start = paths.get(block.start_position_id)
    end = paths.get(block.end_position_id)
    if start is None or end is None:
        raise NotFoundError("No fue posible resolver las posiciones del bloqueo.")
    return schemas.PositionBlockOut(
        id=block.id,
        shelf_id=block.shelf_id,
        start_position=_path_out(start),
        end_position=_path_out(end),
        first_position_number=block.first_position_number,
        last_position_number=block.last_position_number,
        reason=block.reason,
        notes=block.notes,
        blocked_by=block.blocked_by,
        cancelled_at=block.cancelled_at,
        cancelled_by=block.cancelled_by,
        cancellation_reason=block.cancellation_reason,
        created_at=block.created_at,
    )


async def create_block(
    request: Request,
    session: AsyncSession,
    actor: User,
    body: schemas.PositionBlockCreate,
) -> schemas.PositionBlockOut:
    repo = LocationsRepository(session)
    shelf, trays, positions = await repo.get_shelf_structure_for_update(body.shelf_id)
    if shelf is None:
        raise NotFoundError("Anaquel no encontrado.")
    if shelf.version != body.expected_version:
        raise ConflictError(
            "El anaquel fue modificado por otra operacion; recargue y reintente.",
            details={"reason": "stale_version", "current_version": shelf.version},
        )
    if shelf.status != "ACTIVE":
        raise InvalidParameterError("No se puede bloquear un anaquel inactivo.")

    ordered = _sorted_positions(trays, positions)
    index_by_id = {position.id: index for index, position in enumerate(ordered)}
    if body.start_position_id not in index_by_id or body.end_position_id not in index_by_id:
        raise InvalidParameterError(
            "Las posiciones de inicio y fin deben pertenecer al anaquel indicado."
        )
    start_index = index_by_id[body.start_position_id]
    end_index = index_by_id[body.end_position_id]
    if start_index > end_index:
        raise InvalidParameterError("La posicion inicial no puede ser mayor a la posicion final.")

    first_number = start_index + 1
    last_number = end_index + 1
    if await repo.has_overlapping_block(shelf.id, first_number, last_number):
        raise ConflictError(
            "El rango se superpone con un bloqueo activo.",
            details={"reason": "blocked_range_conflict"},
        )
    occupied = await repo.occupied_position_ids(
        [position.id for position in ordered[start_index : end_index + 1]]
    )
    for position in ordered[start_index : end_index + 1]:
        if position.status == "RETIRED":
            raise ConflictError(
                f"La posicion {position.code} esta retirada.",
                details={"reason": "position_retired", "position_id": str(position.id)},
            )
        if position.status == "BLOCKED":
            raise ConflictError(
                f"La posicion {position.code} ya esta bloqueada.",
                details={"reason": "position_blocked", "position_id": str(position.id)},
            )
        if position.id in occupied:
            raise ConflictError(
                f"La posicion {position.code} esta ocupada.",
                details={"reason": "position_occupied", "position_id": str(position.id)},
            )

    block = PositionBlock(
        shelf_id=shelf.id,
        start_position_id=body.start_position_id,
        end_position_id=body.end_position_id,
        first_position_number=first_number,
        last_position_number=last_number,
        reason=body.reason.strip(),
        blocked_by=actor.id,
        notes=clean_optional_text(body.notes, max_length=1000),
    )
    session.add(block)
    for position in ordered[start_index : end_index + 1]:
        position.status = "BLOCKED"
    await session.flush()

    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="position_block.created",
        entity_type="position_block",
        entity_id=block.id,
        after=_block_snapshot(block),
        metadata={
            "shelf_id": str(shelf.id),
            "first_position_number": first_number,
            "last_position_number": last_number,
        },
    )
    await session.commit()
    await session.refresh(block)
    return await _block_out(session, block)


async def cancel_block(
    request: Request,
    session: AsyncSession,
    actor: User,
    block_id: UUID,
    body: schemas.PositionBlockCancel,
) -> schemas.PositionBlockOut:
    block = await session.scalar(
        select(PositionBlock).where(PositionBlock.id == block_id).with_for_update()
    )
    if block is None:
        raise NotFoundError("Bloqueo no encontrado.")
    if block.cancelled_at is not None:
        raise ConflictError(
            "El bloqueo ya fue cancelado.",
            details={
                "reason": "block_already_cancelled",
            },
        )

    repo = LocationsRepository(session)
    shelf, trays, positions = await repo.get_shelf_structure_for_update(block.shelf_id)
    if shelf is None:
        raise NotFoundError("Anaquel no encontrado.")
    if shelf.version != body.expected_version:
        raise ConflictError(
            "El anaquel fue modificado por otra operacion; recargue y reintente.",
            details={"reason": "stale_version", "current_version": shelf.version},
        )

    ordered = _sorted_positions(trays, positions)
    selected = ordered[block.first_position_number - 1 : block.last_position_number]
    occupied = await repo.occupied_position_ids([position.id for position in selected])
    for position in selected:
        if position.id in occupied:
            raise ConflictError(
                f"La posicion {position.code} esta ocupada; no se puede desbloquear.",
                details={"reason": "position_occupied", "position_id": str(position.id)},
            )
        if position.status == "BLOCKED":
            position.status = "AVAILABLE"

    before = _block_snapshot(block)
    block.cancelled_at = datetime.now(UTC)
    block.cancelled_by = actor.id
    block.cancellation_reason = body.reason.strip()
    await session.flush()

    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="position_block.cancelled",
        entity_type="position_block",
        entity_id=block.id,
        before=before,
        after=_block_snapshot(block),
        metadata={"shelf_id": str(shelf.id)},
    )
    await session.commit()
    await session.refresh(block)
    return await _block_out(session, block)


async def list_blocks(
    session: AsyncSession,
    *,
    params: PageParams,
    area_id: UUID | None,
    shelf_id: UUID | None,
    active: bool | None,
) -> Page[schemas.PositionBlockOut]:
    LocationsRepository(session)
    conditions = []
    if area_id:
        conditions.append(Shelf.area_id == area_id)
    if shelf_id:
        conditions.append(PositionBlock.shelf_id == shelf_id)
    if active is True:
        conditions.append(PositionBlock.cancelled_at.is_(None))
    elif active is False:
        conditions.append(PositionBlock.cancelled_at.is_not(None))

    base = select(PositionBlock).join(Shelf, Shelf.id == PositionBlock.shelf_id).where(*conditions)
    total = await session.scalar(select(func.count()).select_from(base.subquery()))
    rows = await session.scalars(
        base.order_by(
            PositionBlock.created_at.desc(),
            PositionBlock.id.desc(),
        )
        .offset(params.offset)
        .limit(params.limit)
    )
    items = [await _block_out(session, block) for block in rows.all()]
    return Page[schemas.PositionBlockOut].build(items, total=int(total or 0), params=params)
