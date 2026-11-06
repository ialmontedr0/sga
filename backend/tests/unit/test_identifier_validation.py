from __future__ import annotations

from typing import cast
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.core.errors import InvalidParameterError
from judicial_archive.modules.case_files import validators
from judicial_archive.modules.case_files.validators import (
    validate_identifier,
    validate_partial_date,
)
from judicial_archive.modules.courts.models import IdentifierFormatProfile


def _profile(*, pattern: str | None, strict: bool) -> IdentifierFormatProfile:
    return IdentifierFormatProfile(
        id=uuid4(),
        court_id=uuid4(),
        identifier_kind="NUC",
        pattern=pattern,
        strict=strict,
        is_active=True,
    )


def _session() -> AsyncSession:
    return cast(AsyncSession, AsyncMock())


@pytest.mark.asyncio
async def test_validate_identifier_without_profile_returns_pending(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _missing(_session: object, **_kwargs: object) -> None:
        return None

    monkeypatch.setattr(validators, "get_active_identifier_profile", _missing)

    result = await validate_identifier(
        _session(),
        court_id=uuid4(),
        kind="NUC",
        raw_value="  nuc-2026-0001 ",
    )

    assert result.normalized == "NUC-2026-0001"
    assert result.verification_status == "PENDING"
    assert result.profile_id is None
    assert result.warning is not None


@pytest.mark.asyncio
async def test_validate_identifier_matching_pattern_is_pending(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = _profile(pattern=r"NUC-\d{4}-\d{4}", strict=True)

    async def _active(_session: object, **_kwargs: object) -> IdentifierFormatProfile:
        return profile

    monkeypatch.setattr(validators, "get_active_identifier_profile", _active)

    result = await validate_identifier(
        _session(),
        court_id=profile.court_id,
        kind="NUC",
        raw_value="nuc-2026-0001",
    )

    assert result.normalized == "NUC-2026-0001"
    assert result.verification_status == "PENDING"
    assert result.profile_id == profile.id
    assert result.warning is None


@pytest.mark.asyncio
async def test_validate_identifier_strict_mismatch_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = _profile(pattern=r"NUC-\d{4}-\d{4}", strict=True)

    async def _active(_session: object, **_kwargs: object) -> IdentifierFormatProfile:
        return profile

    monkeypatch.setattr(validators, "get_active_identifier_profile", _active)

    with pytest.raises(InvalidParameterError) as exc_info:
        await validate_identifier(
            _session(),
            court_id=profile.court_id,
            kind="NUC",
            raw_value="VALOR-INVALIDO",
        )

    assert exc_info.value.details is not None
    assert exc_info.value.details["reason"] == "identifier_pattern_mismatch"


@pytest.mark.asyncio
async def test_validate_identifier_exception_requires_reason(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = _profile(pattern=r"NUC-\d{4}-\d{4}", strict=True)

    async def _active(_session: object, **_kwargs: object) -> IdentifierFormatProfile:
        return profile

    monkeypatch.setattr(validators, "get_active_identifier_profile", _active)

    with pytest.raises(InvalidParameterError) as exc_info:
        await validate_identifier(
            _session(),
            court_id=profile.court_id,
            kind="NUC",
            raw_value="VALOR-INVALIDO",
            allow_exception=True,
        )

    assert exc_info.value.details is not None
    assert exc_info.value.details["reason"] == "exception_reason_required"


@pytest.mark.asyncio
async def test_validate_identifier_exception_with_reason_returns_conflict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = _profile(pattern=r"NUC-\d{4}-\d{4}", strict=True)

    async def _active(_session: object, **_kwargs: object) -> IdentifierFormatProfile:
        return profile

    monkeypatch.setattr(validators, "get_active_identifier_profile", _active)

    result = await validate_identifier(
        _session(),
        court_id=profile.court_id,
        kind="NUC",
        raw_value="VALOR-INVALIDO",
        allow_exception=True,
        exception_reason="Documento historico sin NUC.",
    )

    assert result.verification_status == "CONFLICT"
    assert result.warning is not None


@pytest.mark.asyncio
async def test_validate_identifier_invalid_profile_pattern_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = _profile(pattern="[", strict=True)

    async def _active(_session: object, **_kwargs: object) -> IdentifierFormatProfile:
        return profile

    monkeypatch.setattr(validators, "get_active_identifier_profile", _active)

    with pytest.raises(InvalidParameterError):
        await validate_identifier(
            _session(),
            court_id=profile.court_id,
            kind="NUC",
            raw_value="NUC-2026-0001",
        )


def test_validate_partial_date_accepts_unknown_without_components() -> None:
    validate_partial_date(
        precision="UNKNOWN",
        year=None,
        month=None,
        day=None,
        field="entry",
    )


def test_validate_partial_date_rejects_unknown_with_components() -> None:
    with pytest.raises(InvalidParameterError):
        validate_partial_date(
            precision="UNKNOWN",
            year=2026,
            month=None,
            day=None,
            field="entry",
        )


def test_validate_partial_date_rejects_month_without_year() -> None:
    with pytest.raises(InvalidParameterError):
        validate_partial_date(
            precision="MONTH",
            year=None,
            month=1,
            day=None,
            field="entry",
        )


def test_validate_partial_date_rejects_day_without_month() -> None:
    with pytest.raises(InvalidParameterError):
        validate_partial_date(
            precision="DAY",
            year=2026,
            month=None,
            day=1,
            field="entry",
        )
