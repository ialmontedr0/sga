from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.core.enums import AuditSource, CourtStatus
from judicial_archive.core.errors import ConflictError, InvalidParameterError, NotFoundError
from judicial_archive.core.pagination import Page, PageParams, SortOrder
from judicial_archive.core.text import (
    clean_optional_text,
    normalize_upper_code,
    validate_effective_range,
)
from judicial_archive.modules.audit.services import record_audit_event
from judicial_archive.modules.courts import schemas
from judicial_archive.modules.courts.models import Court
from judicial_archive.modules.courts.repositories import CourtsRepository
from judicial_archive.modules.users.models import User

_ALLOWED_SORT = frozenset({"code_normalized", "name", "status", "created_at", "updated_at"})

_COURT_STATUS_ACTIONS = {
    CourtStatus.ACTIVE.value: "court.activated",
    CourtStatus.INACTIVE.value: "court.deactivated",
}


def court_snapshot(court: Court) -> dict[str, object]:
    return {
        "code_raw": court.code_raw,
        "code_normalized": court.code_normalized,
        "name": court.name,
        "court_type": court.court_type,
        "jurisdiction": court.jurisdiction,
        "status": court.status,
        "effective_from": court.effective_from.isoformat() if court.effective_from else None,
        "effective_to": court.effective_to.isoformat() if court.effective_to else None,
        "source": court.source,
        "notes": court.notes,
    }


def _validate(court_type: str | None, jurisdiction: str | None) -> tuple[str | None, str | None]:
    return (
        clean_optional_text(court_type, max_length=80),
        clean_optional_text(jurisdiction, max_length=120),
    )


async def list_courts(
    session: AsyncSession,
    *,
    params: PageParams,
    q: str | None,
    status: str | None,
    court_type: str | None,
    effective_on: date | None,
    sort_by: str,
    order: SortOrder,
) -> Page[schemas.CourtOut]:
    repo = CourtsRepository(session)
    rows, total = await repo.list_courts(
        q=q,
        status=status,
        court_type=court_type,
        effective_on=effective_on,
        sort_by=sort_by,
        order=order,
        offset=params.offset,
        limit=params.limit,
    )
    items = [schemas.CourtOut.model_validate(row) for row in rows]
    return Page[schemas.CourtOut].build(items, total=total, params=params)


async def get_court(session: AsyncSession, court_id: UUID) -> schemas.CourtOut:
    court = await CourtsRepository(session).get_by_id(court_id)
    if court is None:
        raise NotFoundError("Tribunal no encontrado.")
    return schemas.CourtOut.model_validate(court)


async def create_court(
    request: Request,
    session: AsyncSession,
    actor: User,
    body: schemas.CourtCreate,
) -> schemas.CourtOut:
    validate_effective_range(body.effective_from, body.effective_to)
    court_type, jurisdiction = _validate(body.court_type, body.jurisdiction)
    code_normalized = normalize_upper_code(body.code_raw)
    duplicates = await CourtsRepository(session).count_by_normalized_code(code_normalized)

    court = Court(
        code_raw=body.code_raw.strip(),
        code_normalized=code_normalized,
        name=body.name.strip(),
        court_type=court_type,
        jurisdiction=jurisdiction,
        status=CourtStatus.ACTIVE.value,
        effective_from=body.effective_from,
        effective_to=body.effective_to,
        source=clean_optional_text(body.source, max_length=64),
        notes=clean_optional_text(body.notes, max_length=1000),
    )
    session.add(court)
    await session.flush()

    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="court.created",
        entity_type="court",
        entity_id=court.id,
        after=court_snapshot(court),
        metadata={"duplicate_active_code": duplicates > 0},
        source=AuditSource.API,
    )
    await session.commit()
    await session.refresh(court)
    return schemas.CourtOut.model_validate(court)


async def update_court(
    request: Request,
    session: AsyncSession,
    actor: User,
    court_id: UUID,
    body: schemas.CourtUpdate,
) -> schemas.CourtOut:
    repo = CourtsRepository(session)
    court = await repo.get_by_id(court_id)
    if court is None:
        raise NotFoundError("Tribunal no encontrado.")

    changes = body.model_dump(exclude_unset=True)
    if not changes:
        return schemas.CourtOut.model_validate(court)

    before = court_snapshot(court)
    if "code_raw" in changes:
        code_raw = str(changes["code_raw"]).strip()
        court.code_raw = code_raw
        court.code_normalized = normalize_upper_code(code_raw)
    if "name" in changes:
        court.name = str(changes["name"]).strip()
    if "court_type" in changes:
        court.court_type = clean_optional_text(changes["court_type"], max_length=80)
    if "jurisdiction" in changes:
        court.jurisdiction = clean_optional_text(changes["jurisdiction"], max_length=120)
    if "effective_from" in changes:
        court.effective_from = changes["effective_from"]
    if "effective_to" in changes:
        court.effective_to = changes["effective_to"]
    if "source" in changes:
        court.source = clean_optional_text(changes["source"], max_length=64)
    if "notes" in changes:
        court.notes = clean_optional_text(changes["notes"], max_length=1000)

    validate_effective_range(court.effective_from, court.effective_to)
    await session.flush()
    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="court.updated",
        entity_type="court",
        entity_id=court.id,
        before=before,
        after=court_snapshot(court),
    )
    await session.commit()
    await session.refresh(court)
    return schemas.CourtOut.model_validate(court)


async def set_court_status(
    request: Request,
    session: AsyncSession,
    actor: User,
    court_id: UUID,
    target: CourtStatus,
    reason: str | None,
) -> schemas.CourtOut:
    court = await CourtsRepository(session).get_by_id(court_id)
    if court is None:
        raise NotFoundError("Tribunal no encontrado")
    if court.status == target.value:
        raise ConflictError("El tribunal ya tiene el estado solicitado")
    if target is CourtStatus.INACTIVE and not (reason or "").strip():
        raise InvalidParameterError("La desactivacion requiere un motivo")

    before = court_snapshot(court)
    court.status = target.value
    await session.flush()
    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action=_COURT_STATUS_ACTIONS[target.value],
        entity_type="court",
        entity_id=court.id,
        before=before,
        after=court_snapshot(court),
        metadata={
            "reason": clean_optional_text(reason, max_length=500),
        },
    )
    await session.commit()
    await session.refresh(court)
    return schemas.CourtOut.model_validate(court)
