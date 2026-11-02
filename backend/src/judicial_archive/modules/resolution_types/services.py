from __future__ import annotations

from uuid import UUID

from fastapi import Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.core.errors import ConflictError, InvalidParameterError, NotFoundError
from judicial_archive.core.pagination import Page, PageParams, SortOrder
from judicial_archive.core.text import ensure_resolution_type_code
from judicial_archive.modules.audit.services import record_audit_event
from judicial_archive.modules.courts.models import ResolutionType
from judicial_archive.modules.resolution_types import schemas
from judicial_archive.modules.resolution_types.repositores import ResolutionTypesRepository
from judicial_archive.modules.users.models import User


def _snapshot(item: ResolutionType) -> dict[str, object]:
    return {
        "code": item.code,
        "name": item.name,
        "descritpion": item.description,
        "status": item.status,
    }


async def _get_or_404(repo: ResolutionTypesRepository, item_id: UUID) -> ResolutionType:
    item = await repo.get_by_id(item_id)
    if item is None:
        raise NotFoundError("Tipo de resolucion no encontrado.")
    return item


async def list_resolution_types(
    session: AsyncSession,
    *,
    params: PageParams,
    q: str | None,
    status: str | None,
    sort_by: str,
    order: SortOrder,
) -> Page[schemas.ResolutionTypeOut]:
    rows, total = await ResolutionTypesRepository(session).list_items(
        q=q,
        status=status,
        sort_by=sort_by,
        order=order,
        offset=params.offset,
        limit=params.limit,
    )
    items = [schemas.ResolutionTypeOut.model_validate(row) for row in rows]
    return Page[schemas.ResolutionTypeOut].build(items, total=total, params=params)


async def get_resolution_type(session: AsyncSession, item_id: UUID) -> schemas.ResolutionTypeOut:
    item = await _get_or_404(ResolutionTypesRepository(session), item_id)
    return schemas.ResolutionTypeOut.model_validate(item)


async def create_resolution_type(
    request: Request,
    session: AsyncSession,
    actor: User,
    body: schemas.ResolutionTypeCreate,
) -> schemas.ResolutionTypeOut:
    repo = ResolutionTypesRepository(session)
    code = ensure_resolution_type_code(body.code)
    if await repo.get_by_code(code) is not None:
        raise ConflictError("Ya existe un tipo de resolucion con ese codigo")

    item = ResolutionType(
        code=code,
        name=body.name.strip(),
        description=(body.description or "").strip() or None,
        status="ACTIVE",
    )
    session.add(item)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError("Ya existe un tipo de resolucion con ese codigo.") from exc

    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="resolution_type.created",
        entity_type="resolution_type",
        entity_id=item.id,
        after=_snapshot(item),
    )
    await session.commit()
    await session.refresh(item)
    return schemas.ResolutionTypeOut.model_validate(item)


async def update_resolution_type(
    request: Request,
    session: AsyncSession,
    actor: User,
    item_id: UUID,
    body: schemas.ResolutionTypeUpdate,
) -> schemas.ResolutionTypeOut:
    repo = ResolutionTypesRepository(session)
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
        action="resolution_types.updated",
        entity_type="resolution_type",
        entity_id=item.id,
        before=before,
        after=_snapshot(item),
    )
    await session.commit()
    await session.refresh(item)
    return schemas.ResolutionTypeOut.model_validate(item)


async def set_resolution_type_status(
    request: Request,
    session: AsyncSession,
    actor: User,
    item_id: UUID,
    *,
    active: bool,
    reason: str | None,
) -> schemas.ResolutionTypeOut:
    repo = ResolutionTypesRepository(session)
    item = await _get_or_404(repo, item_id)
    before = _snapshot(item)
    if active:
        item.status = "ACTIVE"
        action = "resolution_type.activated"
    else:
        if not reason or not reason.strip():
            from judicial_archive.core.errors import InvalidParameterError

            raise InvalidParameterError("La desactivacion requiere motivo.")
        item.status = "INACTIVE"
        action = "resolution_type.deactivated"

    await session.flush()
    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action=action,
        entity_type="resolution_type",
        entity_id=item.id,
        before=before,
        after=_snapshot(item),
        metadata={"reason": reason} if reason else None,
    )
    await session.commit()
    await session.refresh(item)
    return schemas.ResolutionTypeOut.model_validate(item)
