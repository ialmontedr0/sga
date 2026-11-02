from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from uuid import UUID

from fastapi import Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.core.errors import ConflictError, InvalidParameterError, NotFoundError
from judicial_archive.core.pagination import Page, PageParams, SortOrder
from judicial_archive.core.text import (
    clean_optional_text,
    ensure_area_code,
    ensure_position_code,
    ensure_shelf_code,
    ensure_tray_code,
)
from judicial_archive.modules.audit.services import record_audit_event
from judicial_archive.modules.locations import capacity, schemas
from judicial_archive.modules.locations.models import Area, Position, Shelf, Tray
from judicial_archive.modules.locations.repositories import LocationsRepository
from judicial_archive.modules.users.models import User


def _area_snapshot(area: Area) -> dict[str, object]:
    return {
        "code": area.code,
        "name": area.name,
        "description": area.description,
        "status": area.status,
    }


def _shelf_snapshot(shelf: Shelf) -> dict[str, object]:
    return {
        "area_id": str(shelf.area_id),
        "code": shelf.code,
        "name": shelf.name,
        "levels": shelf.levels,
        "positions_per_level": shelf.positions_per_level,
        "capacity_positions": shelf.capacity_positions,
        "status": shelf.status,
        "notes": shelf.notes,
    }


def _tray_snapshot(tray: Tray) -> dict[str, object]:
    return {
        "shelf_id": str(tray.shelf_id),
        "code": tray.code,
        "name": tray.name,
        "position_count": tray.position_count,
        "status": tray.status,
        "notes": tray.notes,
    }


def _position_snapshot(position: Position) -> dict[str, object]:
    return {
        "tray_id": str(position.tray_id),
        "code": position.code,
        "label": position.label,
        "status": position.status,
        "notes": position.notes,
    }


async def _flush_or_conflict(session: AsyncSession, message: str) -> None:
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError(message) from exc


async def _recount_tray(session: AsyncSession, tray: Tray) -> None:
    count = await LocationsRepository(session).count_non_retired_positions(tray.id)
    tray.position_count = count or None


def _plan_out(plan: capacity.CapacityPlan) -> schemas.CapacityPlanOut:
    return schemas.CapacityPlanOut(
        shelf_id=plan.shelf_id,
        target_levels=plan.target_levels,
        target_positions_per_level=plan.target_positions_per_level,
        target_total=plan.target_total,
        current_total=plan.current_total,
        trays_to_create=plan.trays_to_create,
        trays_to_reactivate=plan.trays_to_reactivate,
        trays_to_retire=plan.trays_to_retire,
        positions_to_create=plan.positions_to_create,
        positions_to_reactivate=plan.positions_to_reactivate,
        positions_to_retire=plan.positions_to_retire,
        conflicts=[
            schemas.CapacityConflictOut(level=item.level, code=item.code, message=item.message)
            for item in plan.conflicts
        ],
        can_apply=plan.can_apply,
    )


def _positions_by_tray(positions: Sequence[Position]) -> dict[UUID, list[Position]]:
    grouped: dict[UUID, list[Position]] = defaultdict(list)
    for position in positions:
        grouped[position.tray_id].append(position)
    return grouped


async def get_area(session: AsyncSession, area_id: UUID) -> schemas.AreaOut:
    area = await LocationsRepository(session).get_area(area_id)
    if area is None:
        raise NotFoundError("Area no encontrada.")
    return schemas.AreaOut.model_validate(area)


async def get_shelf(session: AsyncSession, shelf_id: UUID) -> schemas.ShelfOut:
    shelf = await LocationsRepository(session).get_shelf(shelf_id)
    if shelf is None:
        raise NotFoundError("Anaquel no encontrado.")
    return schemas.ShelfOut.model_validate(shelf)


async def get_tray(session: AsyncSession, tray_id: UUID) -> schemas.TrayOut:
    tray = await LocationsRepository(session).get_tray(tray_id)
    if tray is None:
        raise NotFoundError("Bandeja no encontrada.")
    return schemas.TrayOut.model_validate(tray)


async def get_position(session: AsyncSession, position_id: UUID) -> schemas.PositionOut:
    position = await LocationsRepository(session).get_position(position_id)
    if position is None:
        raise NotFoundError("Posicion no encontrada.")
    return schemas.PositionOut.model_validate(position)


async def list_areas(
    session: AsyncSession,
    *,
    params: PageParams,
    q: str | None,
    status: str | None,
    sort_by: str,
    order: SortOrder,
) -> Page[schemas.AreaOut]:
    rows, total = await LocationsRepository(session).list_areas(
        q=q,
        status=status,
        sort_by=sort_by,
        order=order,
        offset=params.offset,
        limit=params.limit,
    )
    items = [schemas.AreaOut.model_validate(row) for row in rows]
    return Page[schemas.AreaOut].build(items, total=total, params=params)


async def create_area(
    request: Request, session: AsyncSession, actor: User, body: schemas.AreaCreate
) -> schemas.AreaOut:
    code = ensure_area_code(body.code)
    area = Area(
        code=code,
        name=body.name.strip(),
        description=clean_optional_text(body.description, max_length=500),
        status="ACTIVE",
    )
    session.add(area)
    await _flush_or_conflict(session, "Ya existe un area con ese codigo.")
    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="area.created",
        entity_type="area",
        entity_id=area.id,
        after=_area_snapshot(area),
    )
    await session.commit()
    await session.refresh(area)
    return schemas.AreaOut.model_validate(area)


async def update_area(
    request: Request,
    session: AsyncSession,
    actor: User,
    area_id: UUID,
    body: schemas.AreaUpdate,
) -> schemas.AreaOut:
    area = await LocationsRepository(session).get_area(area_id)
    if area is None:
        raise NotFoundError("Area no encontrada.")
    changes = body.model_dump(exclude_unset=True)
    if not changes:
        return schemas.AreaOut.model_validate(area)
    before = _area_snapshot(area)
    if "code" in changes:
        area.code = ensure_area_code(str(changes["code"]))
    if "name" in changes:
        area.name = str(changes["name"]).strip()
    if "description" in changes:
        area.description = clean_optional_text(changes["description"], max_length=500)
    await _flush_or_conflict(session, "Ya existe un area con ese codigo.")
    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="area.updated",
        entity_type="area",
        entity_id=area.id,
        before=before,
        after=_area_snapshot(area),
    )
    await session.commit()
    await session.refresh(area)
    return schemas.AreaOut.model_validate(area)


async def set_area_status(
    request: Request,
    session: AsyncSession,
    actor: User,
    area_id: UUID,
    target: str,
    reason: str | None,
) -> schemas.AreaOut:
    repo = LocationsRepository(session)
    area = await repo.get_area(area_id)
    if area is None:
        raise NotFoundError("Area no encontrada.")
    if area.status == target:
        raise ConflictError("El area ya tiene el estado solicitado.")
    if target == "INACTIVE":
        if not (reason or "").strip():
            raise InvalidParameterError("La desactivacion requiere un motivo.")
        if await repo.count_active_shelves(area.id) > 0:
            raise ConflictError("No se puede desactivar un area con anaqueles activos.")
    before = _area_snapshot(area)
    area.status = target
    await session.flush()
    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="area.deactivated" if target == "INACTIVE" else "area.activated",
        entity_type="area",
        entity_id=area.id,
        before=before,
        after=_area_snapshot(area),
        metadata={"reason": clean_optional_text(reason, max_length=500)},
    )
    await session.commit()
    await session.refresh(area)
    return schemas.AreaOut.model_validate(area)


async def list_shelves(
    session: AsyncSession,
    *,
    params: PageParams,
    area_id: UUID | None,
    q: str | None,
    status: str | None,
    sort_by: str,
    order: SortOrder,
) -> Page[schemas.ShelfOut]:
    rows, total = await LocationsRepository(session).list_shelves(
        area_id=area_id,
        q=q,
        status=status,
        sort_by=sort_by,
        order=order,
        offset=params.offset,
        limit=params.limit,
    )
    items = [schemas.ShelfOut.model_validate(row) for row in rows]
    return Page[schemas.ShelfOut].build(items, total=total, params=params)


async def create_shelf(
    request: Request, session: AsyncSession, actor: User, body: schemas.ShelfCreate
) -> schemas.ShelfOut:
    repo = LocationsRepository(session)
    area = await repo.get_area(body.area_id)
    if area is None:
        raise NotFoundError("Area no encontrada.")
    if area.status != "ACTIVE":
        raise InvalidParameterError("No se puede crear un anaquel en un area inactiva.")

    shelf = Shelf(
        area_id=area.id,
        code=ensure_shelf_code(body.code),
        name=clean_optional_text(body.name, max_length=120),
        levels=None,
        positions_per_level=None,
        status="ACTIVE",
        notes=clean_optional_text(body.notes, max_length=1000),
    )
    session.add(shelf)
    await _flush_or_conflict(session, "Ya existe un anaquel con ese codigo en el area.")

    plan: capacity.CapacityPlan | None = None
    if body.levels is not None and body.positions_per_level is not None:
        plan = capacity.build_capacity_plan(
            shelf_id=shelf.id,
            target_levels=body.levels,
            positions_per_level=body.positions_per_level,
            trays=[],
            positions_by_tray={},
            occupied_position_ids=set(),
        )
        await capacity.apply_capacity_plan(
            session=session, shelf=shelf, plan=plan, trays_by_id={}, positions_by_id={}
        )

    await session.flush()
    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="shelf.created",
        entity_type="shelf",
        entity_id=shelf.id,
        after=_shelf_snapshot(shelf),
        metadata={
            "capacity": None
            if plan is None
            else {
                "levels": plan.target_levels,
                "positions_per_level": plan.target_positions_per_level,
                "positions_created": plan.positions_to_create,
            }
        },
    )
    await session.commit()
    await session.refresh(shelf)
    return schemas.ShelfOut.model_validate(shelf)


async def update_shelf(
    request: Request,
    session: AsyncSession,
    actor: User,
    shelf_id: UUID,
    body: schemas.ShelfUpdate,
) -> schemas.ShelfOut:
    shelf = await LocationsRepository(session).get_shelf(shelf_id)
    if shelf is None:
        raise NotFoundError("Anaquel no encontrado.")
    changes = body.model_dump(exclude_unset=True)
    if not changes:
        return schemas.ShelfOut.model_validate(shelf)
    before = _shelf_snapshot(shelf)
    if "code" in changes:
        shelf.code = ensure_shelf_code(str(changes["code"]))
    if "name" in changes:
        shelf.name = clean_optional_text(changes["name"], max_length=120)
    if "notes" in changes:
        shelf.notes = clean_optional_text(changes["notes"], max_length=1000)
    await _flush_or_conflict(session, "Ya existe un anaquel con ese codigo en el area.")
    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="shelf.updated",
        entity_type="shelf",
        entity_id=shelf.id,
        before=before,
        after=_shelf_snapshot(shelf),
    )
    await session.commit()
    await session.refresh(shelf)
    return schemas.ShelfOut.model_validate(shelf)


async def preview_capacity(
    session: AsyncSession, shelf_id: UUID, body: schemas.CapacityTarget
) -> schemas.CapacityPlanOut:
    repo = LocationsRepository(session)
    shelf, trays, positions = await repo.get_shelf_structure(shelf_id)
    if shelf is None:
        raise NotFoundError("Anaquel no encontrado.")
    occupied = await repo.occupied_position_ids([position.id for position in positions])
    plan = capacity.build_capacity_plan(
        shelf_id=shelf.id,
        target_levels=body.levels,
        positions_per_level=body.positions_per_level,
        trays=trays,
        positions_by_tray=_positions_by_tray(positions),
        occupied_position_ids=occupied,
    )
    return _plan_out(plan)


async def apply_capacity(
    request: Request,
    session: AsyncSession,
    actor: User,
    shelf_id: UUID,
    body: schemas.CapacityApplyRequest,
) -> schemas.CapacityApplyOut:
    repo = LocationsRepository(session)
    shelf, trays, positions = await repo.get_shelf_structure_for_update(shelf_id)
    if shelf is None:
        raise NotFoundError("Anaquel no encontrado.")
    if shelf.version != body.expected_version:
        raise ConflictError("El anaquel fue modificado por otra operacion; recargue y reintente.")
    if shelf.status != "ACTIVE":
        raise InvalidParameterError("No se puede cambiar la capacidad de un anaquel inactivo.")

    occupied = await repo.occupied_position_ids([position.id for position in positions])
    plan = capacity.build_capacity_plan(
        shelf_id=shelf.id,
        target_levels=body.levels,
        positions_per_level=body.positions_per_level,
        trays=trays,
        positions_by_tray=_positions_by_tray(positions),
        occupied_position_ids=occupied,
    )
    if not plan.can_apply:
        raise ConflictError(
            "La capacidad solicitada entra en conflicto con posiciones ocupadas o bloqueadas.",
            details={"conflicts": [item.__dict__ for item in plan.conflicts]},
        )

    before = _shelf_snapshot(shelf)
    trays_by_id = {tray.id: tray for tray in trays}
    positions_by_id = {position.id: position for position in positions}
    await capacity.apply_capacity_plan(
        session=session,
        shelf=shelf,
        plan=plan,
        trays_by_id=trays_by_id,
        positions_by_id=positions_by_id,
    )
    await session.flush()
    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="shelf.capacity_applied",
        entity_type="shelf",
        entity_id=shelf.id,
        before=before,
        after=_shelf_snapshot(shelf),
        metadata={
            "target_total": plan.target_total,
            "trays_created": plan.trays_to_create,
            "trays_reactivated": plan.trays_to_reactivate,
            "trays_retired": plan.trays_to_retire,
            "positions_created": plan.positions_to_create,
            "positions_reactivated": plan.positions_to_reactivate,
            "positions_retired": plan.positions_to_retire,
        },
    )
    await session.commit()
    await session.refresh(shelf)
    return schemas.CapacityApplyOut(
        shelf=schemas.ShelfOut.model_validate(shelf), plan=_plan_out(plan)
    )


async def set_shelf_status(
    request: Request,
    session: AsyncSession,
    actor: User,
    shelf_id: UUID,
    target: str,
    reason: str | None,
) -> schemas.ShelfOut:
    repo = LocationsRepository(session)
    shelf, trays, positions = await repo.get_shelf_structure_for_update(shelf_id)
    if shelf is None:
        raise NotFoundError("Anaquel no encontrado.")
    if shelf.status == target:
        raise ConflictError("El anaquel ya tiene el estado solicitado.")
    if target == "INACTIVE":
        if not (reason or "").strip():
            raise InvalidParameterError("La desactivacion requiere un motivo.")
        if any(tray.status == "ACTIVE" for tray in trays):
            raise ConflictError("No se puede desactivar un anaquel con bandejas activas.")
        if any(position.status != "RETIRED" for position in positions):
            raise ConflictError("Todas las posiciones deben estar retiradas.")
        if await repo.occupied_position_ids([position.id for position in positions]):
            raise ConflictError("El anaquel tiene posiciones ocupadas.")
    before = _shelf_snapshot(shelf)
    shelf.status = target
    await session.flush()
    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="shelf.deactivated" if target == "INACTIVE" else "shelf.activated",
        entity_type="shelf",
        entity_id=shelf.id,
        before=before,
        after=_shelf_snapshot(shelf),
        metadata={"reason": clean_optional_text(reason, max_length=500)},
    )
    await session.commit()
    await session.refresh(shelf)
    return schemas.ShelfOut.model_validate(shelf)


async def list_trays(
    session: AsyncSession,
    *,
    params: PageParams,
    shelf_id: UUID | None,
    q: str | None,
    status: str | None,
    sort_by: str,
    order: SortOrder,
) -> Page[schemas.TrayOut]:
    rows, total = await LocationsRepository(session).list_trays(
        shelf_id=shelf_id,
        q=q,
        status=status,
        sort_by=sort_by,
        order=order,
        offset=params.offset,
        limit=params.limit,
    )
    items = [schemas.TrayOut.model_validate(row) for row in rows]
    return Page[schemas.TrayOut].build(items, total=total, params=params)


async def create_tray(
    request: Request, session: AsyncSession, actor: User, body: schemas.TrayCreate
) -> schemas.TrayOut:
    repo = LocationsRepository(session)
    shelf = await repo.get_shelf(body.shelf_id)
    if shelf is None:
        raise NotFoundError("Anaquel no encontrado.")
    if shelf.status != "ACTIVE":
        raise InvalidParameterError("No se puede crear una bandeja en un anaquel inactivo.")
    tray = Tray(
        shelf_id=shelf.id,
        code=ensure_tray_code(body.code),
        name=clean_optional_text(body.name, max_length=120),
        position_count=None,
        status="ACTIVE",
        notes=clean_optional_text(body.notes, max_length=1000),
    )
    session.add(tray)
    await _flush_or_conflict(session, "Ya existe una bandeja con ese codigo en el anaquel.")
    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="tray.created",
        entity_type="tray",
        entity_id=tray.id,
        after=_tray_snapshot(tray),
    )
    await session.commit()
    await session.refresh(tray)
    return schemas.TrayOut.model_validate(tray)


async def update_tray(
    request: Request,
    session: AsyncSession,
    actor: User,
    tray_id: UUID,
    body: schemas.TrayUpdate,
) -> schemas.TrayOut:
    tray = await LocationsRepository(session).get_tray(tray_id)
    if tray is None:
        raise NotFoundError("Bandeja no encontrada.")
    changes = body.model_dump(exclude_unset=True)
    if not changes:
        return schemas.TrayOut.model_validate(tray)
    before = _tray_snapshot(tray)
    if "code" in changes:
        tray.code = ensure_tray_code(str(changes["code"]))
    if "name" in changes:
        tray.name = clean_optional_text(changes["name"], max_length=120)
    if "notes" in changes:
        tray.notes = clean_optional_text(changes["notes"], max_length=1000)
    await _flush_or_conflict(session, "Ya existe una bandeja con ese codigo en el anaquel.")
    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="tray.updated",
        entity_type="tray",
        entity_id=tray.id,
        before=before,
        after=_tray_snapshot(tray),
    )
    await session.commit()
    await session.refresh(tray)
    return schemas.TrayOut.model_validate(tray)


async def set_tray_status(
    request: Request,
    session: AsyncSession,
    actor: User,
    tray_id: UUID,
    target: str,
    reason: str | None,
) -> schemas.TrayOut:
    repo = LocationsRepository(session)
    tray, positions = await repo.get_tray_structure_for_update(tray_id)
    if tray is None:
        raise NotFoundError("Bandeja no encontrada.")
    if tray.status == target:
        raise ConflictError("La bandeja ya tiene el estado solicitado.")
    if target == "INACTIVE":
        if not (reason or "").strip():
            raise InvalidParameterError("La desactivacion requiere un motivo.")
        if any(position.status != "RETIRED" for position in positions):
            raise ConflictError("Todas las posiciones deben estar retiradas.")
        occupied = await repo.occupied_position_ids([position.id for position in positions])
        if occupied:
            raise ConflictError("La bandeja tiene posiciones ocupadas.")
    before = _tray_snapshot(tray)
    tray.status = target
    await session.flush()
    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="tray.deactivated" if target == "INACTIVE" else "tray.activated",
        entity_type="tray",
        entity_id=tray.id,
        before=before,
        after=_tray_snapshot(tray),
        metadata={"reason": clean_optional_text(reason, max_length=500)},
    )
    await session.commit()
    await session.refresh(tray)
    return schemas.TrayOut.model_validate(tray)


async def list_positions(
    session: AsyncSession,
    *,
    params: PageParams,
    tray_id: UUID | None,
    q: str | None,
    status: str | None,
    sort_by: str,
    order: SortOrder,
) -> Page[schemas.PositionOut]:
    rows, total = await LocationsRepository(session).list_positions(
        tray_id=tray_id,
        q=q,
        status=status,
        sort_by=sort_by,
        order=order,
        offset=params.offset,
        limit=params.limit,
    )
    items = [schemas.PositionOut.model_validate(row) for row in rows]
    return Page[schemas.PositionOut].build(items, total=total, params=params)


async def create_position(
    request: Request, session: AsyncSession, actor: User, body: schemas.PositionCreate
) -> schemas.PositionOut:
    repo = LocationsRepository(session)
    tray = await repo.get_tray(body.tray_id)
    if tray is None:
        raise NotFoundError("Bandeja no encontrada.")
    if tray.status != "ACTIVE":
        raise InvalidParameterError("No se puede crear una posicion en una bandeja inactiva.")
    position = Position(
        tray_id=tray.id,
        code=ensure_position_code(body.code),
        label=body.label.strip(),
        status="AVAILABLE",
        notes=clean_optional_text(body.notes, max_length=1000),
    )
    session.add(position)
    await _flush_or_conflict(session, "Ya existe una posicion con ese codigo en la bandeja.")
    await _recount_tray(session, tray)
    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="position.created",
        entity_type="position",
        entity_id=position.id,
        after=_position_snapshot(position),
    )
    await session.commit()
    await session.refresh(position)
    return schemas.PositionOut.model_validate(position)


async def update_position(
    request: Request,
    session: AsyncSession,
    actor: User,
    position_id: UUID,
    body: schemas.PositionUpdate,
) -> schemas.PositionOut:
    position = await LocationsRepository(session).get_position(position_id)
    if position is None:
        raise NotFoundError("Posicion no encontrada.")
    changes = body.model_dump(exclude_unset=True)
    if not changes:
        return schemas.PositionOut.model_validate(position)
    before = _position_snapshot(position)
    if "code" in changes:
        position.code = ensure_position_code(str(changes["code"]))
    if "label" in changes:
        position.label = str(changes["label"]).strip()
    if "notes" in changes:
        position.notes = clean_optional_text(changes["notes"], max_length=1000)
    await _flush_or_conflict(session, "Ya existe una posicion con ese codigo en la bandeja.")
    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="position.updated",
        entity_type="position",
        entity_id=position.id,
        before=before,
        after=_position_snapshot(position),
    )
    await session.commit()
    await session.refresh(position)
    return schemas.PositionOut.model_validate(position)


async def retire_position(
    request: Request,
    session: AsyncSession,
    actor: User,
    position_id: UUID,
    body: schemas.PositionRetireRequest,
) -> schemas.PositionOut:
    repo = LocationsRepository(session)
    position = await repo.get_position(position_id)
    if position is None:
        raise NotFoundError("Posicion no encontrada.")
    if position.status == "RETIRED":
        raise ConflictError("La posicion ya esta retirada.")
    if position.status == "BLOCKED":
        raise ConflictError("No se puede retirar una posicion bloqueada.")
    if await repo.is_position_occupied(position.id):
        raise ConflictError("No se puede retirar una posicion ocupada.")
    before = _position_snapshot(position)
    position.status = "RETIRED"
    tray = await repo.get_tray(position.tray_id)
    if tray is not None:
        await _recount_tray(session, tray)
    await session.flush()
    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="position.retired",
        entity_type="position",
        entity_id=position.id,
        before=before,
        after=_position_snapshot(position),
        metadata={"reason": body.reason.strip()},
    )
    await session.commit()
    await session.refresh(position)
    return schemas.PositionOut.model_validate(position)


async def activate_position(
    request: Request, session: AsyncSession, actor: User, position_id: UUID
) -> schemas.PositionOut:
    repo = LocationsRepository(session)
    position = await repo.get_position(position_id)
    if position is None:
        raise NotFoundError("Posicion no encontrada.")
    if position.status == "AVAILABLE":
        raise ConflictError("La posicion ya esta disponible.")
    if position.status == "BLOCKED":
        raise ConflictError("Use el flujo de desbloqueo de B6.")
    before = _position_snapshot(position)
    position.status = "AVAILABLE"
    tray = await repo.get_tray(position.tray_id)
    if tray is not None:
        await _recount_tray(session, tray)
    await session.flush()
    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="position.activated",
        entity_type="position",
        entity_id=position.id,
        before=before,
        after=_position_snapshot(position),
    )
    await session.commit()
    await session.refresh(position)
    return schemas.PositionOut.model_validate(position)
