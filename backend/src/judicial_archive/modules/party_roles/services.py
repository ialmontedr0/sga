from __future__ import annotations

from uuid import UUID

from fastapi import Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.core.errors import ConflictError, InvalidParameterError, NotFoundError
from judicial_archive.core.pagination import Page, PageParams, SortOrder
from judicial_archive.core.text import ensure_party_role_code
from judicial_archive.modules.audit.services import record_audit_event
from judicial_archive.modules.courts.models import PartyRole
from judicial_archive.modules.party_roles import schemas
from judicial_archive.modules.party_roles.repositories import PartyRolesRepository
from judicial_archive.modules.users.models import User


def _snapshot(item: PartyRole) -> dict[str, object]:
    return {
        "code": item.code,
        "name": item.name,
        "description": item.description,
        "is_system": item.is_system,
        "status": item.status,
    }


async def _get_or_404(repo: PartyRolesRepository, item_id: UUID) -> PartyRole:
    item = await repo.get_by_id(item_id)
    if item is None:
        raise NotFoundError("Rol de parte no encontrado.")
    return item


async def list_party_roles(
    session: AsyncSession,
    *,
    params: PageParams,
    q: str | None,
    status: str | None,
    sort_by: str,
    order: SortOrder,
) -> Page[schemas.PartyRoleOut]:
    rows, total = await PartyRolesRepository(session).list_items(
        q=q,
        status=status,
        sort_by=sort_by,
        order=order,
        offset=params.offset,
        limit=params.limit,
    )
    items = [schemas.PartyRoleOut.model_validate(row) for row in rows]
    return Page[schemas.PartyRoleOut].build(items, total=total, params=params)


async def get_party_role(session: AsyncSession, item_id: UUID) -> schemas.PartyRoleOut:
    item = await _get_or_404(PartyRolesRepository(session), item_id)
    return schemas.PartyRoleOut.model_validate(item)


async def create_party_role(
    request: Request,
    session: AsyncSession,
    actor: User,
    body: schemas.PartyRoleCreate,
) -> schemas.PartyRoleOut:
    repo = PartyRolesRepository(session)
    code = ensure_party_role_code(body.code)
    if await repo.get_by_code(code) is not None:
        raise ConflictError("Ya existe un rol de parte con ese codigo.")
    item = PartyRole(
        code=code,
        name=body.name.strip(),
        description=(body.description or "").strip() or None,
        is_system=False,
        status="ACTIVE",
    )
    session.add(item)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError("Ya existe un rol de parte con ese codigo.") from exc
    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="party_role.created",
        entity_type="party_role",
        entity_id=item.id,
        after=_snapshot(item),
    )
    await session.commit()
    await session.refresh(item)
    return schemas.PartyRoleOut.model_validate(item)


async def update_party_role(
    request: Request,
    session: AsyncSession,
    actor: User,
    item_id: UUID,
    body: schemas.PartyRoleUpdate,
) -> schemas.PartyRoleOut:
    repo = PartyRolesRepository(session)
    item = await _get_or_404(repo, item_id)
    before = _snapshot(item)
    changes = body.model_dump(exclude_unset=True)
    if changes.get("name") is not None:
        name = changes["name"].strip()
        if not name:
            raise InvalidParameterError("El nombre no puede estar vacio.")
        item.name = name
    if "description" in changes:
        item.description = (changes["description"] or "").strip() or None
    await session.flush()
    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="party_role.updated",
        entity_type="party_role",
        entity_id=item.id,
        before=before,
        after=_snapshot(item),
    )
    await session.commit()
    await session.refresh(item)
    return schemas.PartyRoleOut.model_validate(item)


async def set_party_role_status(
    request: Request,
    session: AsyncSession,
    actor: User,
    item_id: UUID,
    *,
    active: bool,
    reason: str | None,
) -> schemas.PartyRoleOut:
    repo = PartyRolesRepository(session)
    item = await _get_or_404(repo, item_id)
    if not active and item.is_system:
        raise InvalidParameterError("No se puede desactivar un rol de sistema.")
    before = _snapshot(item)
    if active:
        item.status = "ACTIVE"
        action = "party_role.activated"
    else:
        if not reason or not reason.strip():
            raise InvalidParameterError("La desactivacion requiere motivo.")
        item.status = "INACTIVE"
        action = "party_role.deactivated"
    await session.flush()
    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action=action,
        entity_type="party_role",
        entity_id=item.id,
        before=before,
        after=_snapshot(item),
        metadata={"reason": reason} if reason else None,
    )
    await session.commit()
    await session.refresh(item)
    return schemas.PartyRoleOut.model_validate(item)
