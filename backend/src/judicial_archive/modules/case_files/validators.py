from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.core.enums import IdentifierKind, VerificationStatus
from judicial_archive.core.errors import InvalidParameterError
from judicial_archive.modules.courts.models import IdentifierFormatProfile

_WHITESPACE = re.compile(r"\s+")


def normalize_identifier(value: str) -> str:
    cleaned = value.strip().upper()
    if not cleaned:
        raise InvalidParameterError("El identificador no puede estar vacio.")
    return _WHITESPACE.sub("", cleaned)


def normalize_person_name(value: str) -> str:
    cleaned = "".join(value.strip().split())
    if not cleaned:
        raise InvalidParameterError("El nombre no puede estar vacio.")
    decomposed = unicodedata.normalize("NFKD", cleaned)
    without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
    return without_accents.upper()


@dataclass(frozen=True)
class IdentifierValidation:
    raw: str
    normalized: str
    verification_status: str
    profile_id: UUID | None
    warning: str | None = None


async def get_active_identifier_profile(
    session: AsyncSession,
    *,
    court_id: UUID,
    kind: str,
    on_date: date,
) -> IdentifierFormatProfile | None:
    return await session.scalar(
        select(IdentifierFormatProfile)
        .where(
            IdentifierFormatProfile.court_id == court_id,
            IdentifierFormatProfile.identifier_kind == kind,
            IdentifierFormatProfile.is_active.is_(True),
            IdentifierFormatProfile.effective_from <= on_date,
            or_(
                IdentifierFormatProfile.effective_to.is_(None),
                IdentifierFormatProfile.effective_to >= on_date,
            ),
        )
        .order_by(IdentifierFormatProfile.effective_from.desc())
        .limit(1)
    )


async def validate_identifier(
    session: AsyncSession,
    *,
    court_id: UUID,
    kind: str,
    raw_value: str,
    allow_exception: bool = False,
    exception_reason: str | None = None,
    on_date: date | None = None,
) -> IdentifierValidation:
    raw = raw_value.strip()
    normalized = normalize_identifier(raw)
    profile = await get_active_identifier_profile(
        session,
        court_id=court_id,
        kind=kind,
        on_date=on_date or date.today(),  # noqa: DTZ011
    )
    if profile is None:
        return IdentifierValidation(
            raw=raw,
            normalized=normalized,
            verification_status=VerificationStatus.PENDING.value,
            profile_id=None,
            warning="No hay perfil de identificador activo para el tribunal.",
        )

    if not profile.pattern:
        return IdentifierValidation(
            raw=raw,
            normalized=normalized,
            verification_status=VerificationStatus.PENDING.value,
            profile_id=profile.id,
            warning="El perfil activo no define patron.",
        )

    try:
        matches = re.fullmatch(profile.pattern, normalized) is not None
    except re.error as exc:
        raise InvalidParameterError(
            "El perfil de identificador contiene un patron invalido.",
            details={"profile_id": str(profile.id)},
        ) from exc

    if matches:
        return IdentifierValidation(
            raw=raw,
            normalized=normalized,
            verification_status=VerificationStatus.PENDING.value,
            profile_id=profile.id,
        )

    if profile.strict and not allow_exception:
        raise InvalidParameterError(
            "El identificador no cumple el patron configurado para el tribunal.",
            details={
                "reason": "identifier_pattern_mismatch",
                "profile_id": str(profile.id),
                "kind": kind,
                "normalized": normalized,
            },
        )

    if allow_exception and not (exception_reason or "").strip():
        raise InvalidParameterError(
            "La excepcion de identificador requiere un motivo.",
            details={"reason": "exception_reason_required"},
        )

    return IdentifierValidation(
        raw=raw,
        normalized=normalized,
        verification_status=VerificationStatus.CONFLICT.value,
        profile_id=profile.id,
        warning="El identificador no cumple el patron; se registro como excepcion.",
    )


def validate_partial_date(
    *,
    precision: str,
    year: int | None,
    month: int | None,
    day: int | None,
    field: str,
) -> None:
    valid = {"UNKNOWN", "YEAR", "MONTH", "DAY"}
    if precision not in valid:
        raise InvalidParameterError(f"Precision invalida para {field}.")
    if precision == "UNKNOWN":
        if year is not None or month is not None or day is not None:
            raise InvalidParameterError(f"{field} UNKNOWN no admite componentes.")
        return
    if year is None:
        raise InvalidParameterError(f"{field} requiere anio.")
    if precision == "YEAR":
        if month is not None or day is not None:
            raise InvalidParameterError(f"{field} YEAR no admite mes ni dia.")
        return
    if month is None:
        raise InvalidParameterError(f"{field} requiere mes.")
    if precision == "MONTH":
        if day is not None:
            raise InvalidParameterError(f"{field} MONTH no admite dia.")
        return
    if day is None:
        raise InvalidParameterError(f"{field} requiere dia.")


def identifier_kind_for_resolution() -> str:
    return IdentifierKind.SENTENCE.value
