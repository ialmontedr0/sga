from __future__ import annotations

import re
from datetime import date, timedelta
from uuid import UUID

from fastapi import Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.core.errors import ConflictError, InvalidParameterError, NotFoundError
from judicial_archive.core.pagination import Page, PageParams
from judicial_archive.core.text import validate_effective_range
from judicial_archive.modules.audit.services import record_audit_event
from judicial_archive.modules.courts.models import Court, IdentifierFormatProfile
from judicial_archive.modules.identifier_profiles import schemas
from judicial_archive.modules.identifier_profiles.repositores import IdentifierProfilesRepository
from judicial_archive.modules.users.models import User

_NESTED_QUANTIFIER = re.compile(
    r"\((?:[^()]|\([^()]*\))*[+*][^()]*\)[+*{]"
    r"|\[[^\]]*[+*][^\]]*\][+*{]"
)

_NUMERIC_BACKREF = re.compile(r"\\[1-9]")


def _snapshot(profile: IdentifierFormatProfile) -> dict[str, object]:
    return {
        "court_id": str(profile.court_id),
        "identifier_kind": profile.identifier_kind,
        "pattern": profile.pattern,
        "strict": profile.strict,
        "is_active": profile.is_active,
        "effective_from": profile.effective_from.isoformat(),
        "effective_to": profile.effective_to.isoformat() if profile.effective_to else None,
        "notes": profile.notes,
    }


async def _get_or_404(
    repo: IdentifierProfilesRepository,
    profile_id: UUID,
) -> IdentifierFormatProfile:
    profile = await repo.get_by_id(profile_id)
    if profile is None:
        raise NotFoundError("Perfil de identificador no encontrado.")
    return profile


async def _require_active_court(session: AsyncSession, court_id: UUID) -> Court:
    court = await session.get(Court, court_id)
    if court is None:
        raise NotFoundError("Tribunal no encontrado.")
    if court.status != "ACTIVE":
        raise InvalidParameterError("No se puede crear un perfil para un tribunal activo.")
    return court


async def list_identifier_profiles(
    session: AsyncSession,
    *,
    params: PageParams,
    court_id: UUID | None,
    identifier_kind: str | None,
    is_active: bool | None,
) -> Page[schemas.IdentifierProfileOut]:
    rows, total = await IdentifierProfilesRepository(session).list_profiles(
        court_id=court_id,
        identifier_kind=identifier_kind,
        is_active=is_active,
        offset=params.offset,
        limit=params.limit,
    )
    items = [schemas.IdentifierProfileOut.model_validate(row) for row in rows]
    return Page[schemas.IdentifierProfileOut].build(items, total=total, params=params)


async def get_identifier_profile(
    session: AsyncSession,
    profile_id: UUID,
) -> schemas.IdentifierProfileOut:
    profile = await _get_or_404(IdentifierProfilesRepository(session), profile_id)
    return schemas.IdentifierProfileOut.model_validate(profile)


async def create_identifier_profile(
    request: Request,
    session: AsyncSession,
    actor: User,
    body: schemas.IdentifierProfileCreate,
) -> schemas.IdentifierProfileOut:
    await _require_active_court(session, body.court_id)
    effective_from = body.effective_from or date.today()  # noqa: DTZ011
    validate_identifier_pattern(
        pattern=body.pattern,
        examples=body.examples,
        rejects=body.rejects,
        strict=body.strict,
        effective_from=effective_from,
        effective_to=body.effective_to,
    )

    repo = IdentifierProfilesRepository(session)
    if await repo.get_active_for_update(body.court_id, body.identifier_kind) is not None:
        raise ConflictError("Ya existe un perfil activo para ese tribunal y tipo; use /replace.")

    profile = IdentifierFormatProfile(
        court_id=body.court_id,
        identifier_kind=body.identifier_kind,
        pattern=body.pattern,
        tokens=body.tokens,
        examples=body.examples,
        rejects=body.rejects,
        strict=body.strict,
        is_active=True,
        effective_from=effective_from,
        effective_to=body.effective_to,
        notes=body.notes,
    )
    session.add(profile)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError("Ya existe un perfil activo para ese tribunal y tipo.") from exc

    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="identifier_profile.created",
        entity_type="identifier_profile",
        entity_id=profile.id,
        after=_snapshot(profile),
    )
    await session.commit()
    await session.refresh(profile)
    return schemas.IdentifierProfileOut.model_validate(profile)


async def replace_identifier_profile(
    request: Request,
    session: AsyncSession,
    actor: User,
    profile_id: UUID,
    body: schemas.IdentifierProfileReplace,
) -> schemas.IdentifierProfileOut:
    repo = IdentifierProfilesRepository(session)
    old = await _get_or_404(repo, profile_id)
    if not old.is_active:
        raise ConflictError("El perfil indicado no esta activo.")
    if body.effective_from <= old.effective_from:
        raise InvalidParameterError(
            "La nueva vigencia debe comenzar despues de la vigencia del perfil anterior."
        )
    validate_identifier_pattern(
        pattern=body.pattern,
        examples=body.examples,
        rejects=body.rejects,
        strict=body.strict,
        effective_from=body.effective_from,
        effective_to=None,
    )

    old_end = body.effective_from - timedelta(days=1)
    before = _snapshot(old)
    old.is_active = False
    if old.effective_to is None or old.effective_to > old_end:
        old.effective_to = old_end
    await session.flush()

    new = IdentifierFormatProfile(
        court_id=old.court_id,
        identifier_kind=old.identifier_kind,
        pattern=body.pattern,
        tokens=body.tokens,
        examples=body.examples,
        rejects=body.rejects,
        strict=body.strict,
        is_active=True,
        effective_from=body.effective_from,
        effective_to=None,
        notes=body.notes,
    )
    session.add(new)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError("No se pudo reemplazar el perfil; recargue y reintente.") from exc

    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="identifier_profile.replaced",
        entity_type="identifier_profile",
        entity_id=new.id,
        before=before,
        after=_snapshot(new),
    )
    await session.commit()
    await session.refresh(new)
    return schemas.IdentifierProfileOut.model_validate(new)


async def update_identifier_profile(
    request: Request,
    session: AsyncSession,
    actor: User,
    profile_id: UUID,
    body: schemas.IdentifierProfileUpdate,
) -> schemas.IdentifierProfileOut:
    repo = IdentifierProfilesRepository(session)
    profile = await _get_or_404(repo, profile_id)
    before = _snapshot(profile)
    changes = body.model_dump(exclude_unset=True)
    if "notes" in changes:
        profile.notes = changes["notes"]
    if "effective_to" in changes:
        profile.effective_to = changes["effective_to"]
        validate_effective_range(profile.effective_from, profile.effective_to)
    await session.flush()
    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="identifier_profile.updated",
        entity_type="identifier_profile",
        entity_id=profile.id,
        before=before,
        after=_snapshot(profile),
    )
    await session.commit()
    await session.refresh(profile)
    return schemas.IdentifierProfileOut.model_validate(profile)


async def set_identifier_profile_status(
    request: Request,
    session: AsyncSession,
    actor: User,
    profile_id: UUID,
    *,
    active: bool,
    reason: str | None,
) -> schemas.IdentifierProfileOut:
    repo = IdentifierProfilesRepository(session)
    profile = await _get_or_404(repo, profile_id)
    if active and profile.is_active:
        return schemas.IdentifierProfileOut.model_validate(profile)
    before = _snapshot(profile)

    if active:
        if await repo.get_active_for_update(profile.court_id, profile.identifier_kind) is not None:
            raise ConflictError("Ya existe un perfil activo para ese tribunal y tipo.")
        profile.is_active = True
        action = "identifier_profile.activated"
    else:
        if not reason or not reason.strip():
            raise InvalidParameterError("La desactivacion requiere motivo.")
        profile.is_active = False
        action = "identifier_profile.deactivated"

    await session.flush()
    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action=action,
        entity_type="identifier_profile",
        entity_id=profile.id,
        before=before,
        after=_snapshot(profile),
        metadata={"reason": reason} if reason else None,
    )
    await session.commit()
    await session.refresh(profile)
    return schemas.IdentifierProfileOut.model_validate(profile)


def validate_identifier_pattern(
    *,
    pattern: str | None,
    examples: list[str] | None,
    rejects: list[str] | None,
    strict: bool,
    effective_from: date,
    effective_to: date | None,
) -> None:
    validate_effective_range(effective_from, effective_to)
    if strict and not pattern:
        raise InvalidParameterError("Un perfil estricto requiere patron.")
    if not pattern:
        return
    if len(pattern) > 255:
        raise InvalidParameterError("El patron supera 255 caracteres.")
    if _NESTED_QUANTIFIER.search(pattern):
        raise InvalidParameterError(
            "El patron contiene cuantificadores anidados potencialmente peligrosos."
        )
    if _NUMERIC_BACKREF.search(pattern):
        raise InvalidParameterError("El patron admite retroreferencias numericas.")

    try:
        compiled = re.compile(pattern)
    except re.error as exc:
        raise InvalidParameterError(
            "El patron no es una expresion regular valida.", details={"error": str(exc)}
        ) from exc

    cleaned_examples = examples or []
    if strict and len(cleaned_examples) < 3:
        raise InvalidParameterError("Un perfil estricto requiere al menos 3 ejemplos.")

    invalid_examples = [item for item in cleaned_examples if compiled.fullmatch(item) is None]
    if invalid_examples:
        raise InvalidParameterError(
            "Uno o mas ejemplos no cumplen el patron.",
            details={"invalid_examples": invalid_examples[:10]},
        )

    accepted_rejects = [item for item in (rejects or []) if compiled.fullmatch(item) is not None]
    if accepted_rejects:
        raise InvalidParameterError(
            "Uno o mass rechazos cumplen con el patron.",
            details={"invalid_rejects": accepted_rejects[:10]},
        )
