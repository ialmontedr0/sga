from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import Request
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.core.errors import ConflictError, InvalidParameterError, NotFoundError
from judicial_archive.core.pagination import Page, PageParams, SortOrder
from judicial_archive.core.text import ensure_sequence_name, validate_effective_range
from judicial_archive.modules.audit.services import record_audit_event
from judicial_archive.modules.courts.models import Court, NumberingPolicy
from judicial_archive.modules.numbering import schemas
from judicial_archive.modules.numbering.repositores import NumberingPoliciesRepository
from judicial_archive.modules.users.models import User

_SCOPE_REQUIRED = {
    "GLOBAL": (False, False, False),
    "COURT": (True, False, False),
    "BOX_TYPE": (False, True, False),
    "YEAR": (False, False, True),
}


def validate_scope_columns(
    *,
    scope: str,
    court_id: UUID | None,
    box_type: str | None,
    year: int | None,
) -> None:
    try:
        require_court, require_box_type, require_year = _SCOPE_REQUIRED[scope]
    except KeyError as exc:
        raise InvalidParameterError("Alcance de numeracion invalido.") from exc
    if (court_id is not None) is not require_court:
        raise InvalidParameterError("El alcance y el tribunal no son coherentes")
    if (box_type is not None) is not require_box_type:
        raise InvalidParameterError("El alcance y el tipo de caja no son coherentes.")
    if (year is not None) is not require_year:
        raise InvalidParameterError("El alcance y el anio no son coherentes.")


def format_visible_number(policy: NumberingPolicy, value: int) -> str:
    if value < 1:
        raise InvalidParameterError("El valor de numeracion debe ser positivo.")
    number = str(value).zfill(policy.padding)
    formatted = f"{policy.prefix or ''}{number}{policy.suffix or ''}"
    if len(formatted) > 32:
        raise InvalidParameterError(
            "El numero visible formateado supera 32 caracteres.",
            details={"formatted_length": len(formatted)},
        )
    return formatted


## Verificar existencia de secuencia
async def _sequence_exists(session: AsyncSession, name: str) -> bool:
    result = await session.scalar(text("SELECT to_regclass(:name)"), {"name": f"public.{name}"})
    return result is not None


## Crear secuencia
async def create_sequence(
    session: AsyncSession,
    *,
    sequence_name: str,
    start_value: int,
    step: int,
) -> None:
    name = ensure_sequence_name(sequence_name)
    if await _sequence_exists(session, name):
        raise ConflictError("La secuencia ya existe")
    await session.execute(
        text(f'CREATE SEQUENCE "{name}" START WITH {int(start_value)} INCREMENT BY {int(step)}')
    )


def validate_format_capacity(policy: NumberingPolicy) -> None:
    probe = format_visible_number(policy, max(policy.start_value, 1))
    if len(probe) > 32:
        raise InvalidParameterError("La configuracion produce numeros visibles demasiado largos.")


def _snapshot(policy: NumberingPolicy) -> dict[str, object]:
    return {
        "code": policy.code,
        "scope": policy.scope,
        "court_id": str(policy.court_id) if policy.court_id else None,
        "box_type": policy.box_type,
        "year": policy.year,
        "sequence_name": policy.sequence_name,
        "prefix": policy.prefix,
        "suffix": policy.suffix,
        "padding": policy.padding,
        "start_value": policy.start_value,
        "step": policy.step,
        "reset_policy": policy.reset_policy,
        "is_active": policy.is_active,
        "effective_from": policy.effective_from.isoformat(),
        "effective_to": policy.effective_to.isoformat() if policy.effective_to else None,
    }


async def _get_or_404(repo: NumberingPoliciesRepository, policy_id: UUID) -> NumberingPolicy:
    policy = await repo.get_by_id(policy_id)
    if policy is None:
        raise NotFoundError("Politica de numeracion no encontrada.")
    return policy


async def list_numbering_policies(
    session: AsyncSession,
    *,
    params: PageParams,
    q: str | None,
    scope: str | None,
    is_active: bool | None,
    court_id: UUID | None,
    sort_by: str,
    order: SortOrder,
) -> Page[schemas.NumberingPolicyOut]:
    rows, total = await NumberingPoliciesRepository(session).list_items(
        q=q,
        scope=scope,
        is_active=is_active,
        court_id=court_id,
        sort_by=sort_by,
        order=order,
        offset=params.offset,
        limit=params.limit,
    )
    items = [schemas.NumberingPolicyOut.model_validate(row) for row in rows]
    return Page[schemas.NumberingPolicyOut].build(items, total=total, params=params)


async def get_numbering_policy(
    session: AsyncSession, policy_id: UUID
) -> schemas.NumberingPolicyOut:
    policy = await _get_or_404(NumberingPoliciesRepository(session), policy_id)
    return schemas.NumberingPolicyOut.model_validate(policy)


async def create_numbering_policy(
    request: Request, session: AsyncSession, actor: User, body: schemas.NumberingPolicyCreate
) -> schemas.NumberingPolicyOut:
    code = body.code.strip().upper()
    sequence_name = ensure_sequence_name(body.sequence_name)
    validate_scope_columns(
        scope=body.scope, court_id=body.court_id, box_type=body.box_type, year=body.year
    )

    repo = NumberingPoliciesRepository(session)
    if await repo.get_by_code(code) is not None:
        raise ConflictError("Ya existe una politica con ese codigo.")
    if await repo.get_by_sequence_name(sequence_name) is not None:
        raise ConflictError("Ya existe una politica con ese nombre de secuencia.")
    if body.scope == "COURT":
        court = await session.get(Court, body.court_id)
        if court is None:
            raise NotFoundError("Tribunal no encontrado.")
        if court.status != "ACTIVE":
            raise InvalidParameterError("El tribunal esta inactivo.")

    effective_from = body.effective_from or date.today()  # noqa: DTZ011
    validate_effective_range(effective_from, body.effective_to)

    if (
        await repo.get_active_for_update(
            scope=body.scope,
            court_id=body.court_id,
            box_type=body.box_type,
            year=body.year,
        )
        is not None
    ):
        raise ConflictError("Ya existe una politica para ese alcance.")

    policy = NumberingPolicy(
        code=code,
        description=(body.description or "").strip() or None,
        scope=body.scope,
        court_id=body.court_id,
        box_type=body.box_type,
        year=body.year,
        sequence_name=sequence_name,
        prefix=body.prefix,
        suffix=body.suffix,
        padding=body.padding,
        start_value=body.start_value,
        step=body.step,
        reset_policy="NEVER",
        is_active=True,
        effective_from=effective_from,
        effective_to=body.effective_to,
        notes=body.notes,
    )
    validate_format_capacity(policy)
    session.add(policy)
    try:
        await session.flush()
        await create_sequence(
            session,
            sequence_name=sequence_name,
            start_value=body.start_value,
            step=body.step,
        )
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError("No se pudo crear la politica de numeracion.") from exc

    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="numbering_policy.created",
        entity_type="numbering_policy",
        entity_id=policy.id,
        after=_snapshot(policy),
    )
    await session.commit()
    await session.refresh(policy)
    return schemas.NumberingPolicyOut.model_validate(policy)


async def update_numbering_policy(
    request: Request,
    session: AsyncSession,
    actor: User,
    policy_id: UUID,
    body: schemas.NumberingPolicyUpdate,
) -> schemas.NumberingPolicyOut:
    repo = NumberingPoliciesRepository(session)
    policy = await _get_or_404(repo, policy_id)
    before = _snapshot(policy)
    changes = body.model_dump(exclude_unset=True)
    if "description" in changes:
        policy.description = (changes["description"] or "").strip() or None
    if "notes" in changes:
        policy.notes = changes["notes"]
    if "effective_to" in changes:
        policy.effective_to = changes["effective_to"]
        validate_effective_range(policy.effective_from, policy.effective_to)
    await session.flush()
    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="numbering_policy.updated",
        entity_type="numbering_policy",
        entity_id=policy.id,
        before=before,
        after=_snapshot(policy),
    )
    await session.commit()
    await session.refresh(policy)
    return schemas.NumberingPolicyOut.model_validate(policy)


async def set_numbering_policy_status(
    request: Request,
    session: AsyncSession,
    actor: User,
    policy_id: UUID,
    *,
    active: bool,
    reason: str | None,
) -> schemas.NumberingPolicyOut:
    repo = NumberingPoliciesRepository(session)
    policy = await _get_or_404(repo, policy_id)
    before = _snapshot(policy)

    if active:
        if not await _sequence_exists(session, policy.sequence_name):
            raise ConflictError("La secuencia de la politica no existe.")
        other = await repo.get_active_for_update(
            scope=policy.scope,
            court_id=policy.court_id,
            box_type=policy.box_type,
            year=policy.year,
        )
        if other is not None and other.id != policy.id:
            raise ConflictError("Ya existe otra politica activa para ese alcance.")
        policy.is_active = True
        action = "numbering_policy.activated"
    else:
        if not reason or not reason.strip():
            raise InvalidParameterError("La desactivacion requiere motivo.")
        policy.is_active = False
        action = "numbering_policy.deactivated"

    await session.flush()
    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action=action,
        entity_type="numbering_policy",
        entity_id=policy.id,
        before=before,
        after=_snapshot(policy),
        metadata={"reason": reason} if reason else None,
    )
    await session.commit()
    await session.refresh(policy)
    return schemas.NumberingPolicyOut.model_validate(policy)


async def preview_numbering_policy(
    session: AsyncSession,
    policy_id: UUID,
    value: int,
) -> schemas.NumberingPreviewOut:
    policy = await _get_or_404(NumberingPoliciesRepository(session), policy_id)
    return schemas.NumberingPreviewOut(
        policy_id=policy.id, value=value, formatted=format_visible_number(policy, value)
    )
