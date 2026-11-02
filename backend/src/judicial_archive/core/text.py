from __future__ import annotations

import re
from datetime import date

from judicial_archive.core.errors import InvalidParameterError

_SEQUENCE_NAME = re.compile(r"^[a-z][a-z0-9_]{2,62}$")
_POSITION_CODE = re.compile(r"^[A-Z0-9][A-Z0-9-]{0,31}$")
_TRAY_CODE = re.compile(r"^[A-Z0-9][A-Z0-9-]{0,15}$")
_SHELF_CODE = re.compile(r"^[A-Z0-9][A-Z0-9-]{0,15}$")
_AREA_CODE = re.compile(r"^[A-Z][A-Z0-9-]{0,15}$")
_RESOLUTION_TYPE_CODE = re.compile(r"^[A-Z][A-Z0-9_]{1,31}$")
_PARTY_ROLE_CODE = re.compile(r"^[A-Z][A-Z0-9_]{1,63}$")
_SETTING_KEY = re.compile(r"^[a-z][a-z0-9_.-]{2,127}$")


def normalize_upper_code(value: str) -> str:
    return value.strip().upper()


def normalize_lower_key(value: str) -> str:
    return value.strip().lower()


def clean_optional_text(value: str | None, *, max_length: int) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if len(cleaned) > max_length:
        raise InvalidParameterError(
            "El texto supera la longitud permitida.", details={"max_length": max_length}
        )
    return cleaned


def ensure_pattern(value: str, pattern: re.Pattern[str], *, field: str, message: str) -> str:
    cleaned = value.strip()
    if not pattern.fullmatch(cleaned):
        raise InvalidParameterError(message, details={"field": field})
    return cleaned


def ensure_area_code(value: str) -> str:
    return ensure_pattern(
        normalize_upper_code(value),
        _AREA_CODE,
        field="code",
        message="El codigo de area no tiene un formato valido.",
    )


def ensure_resolution_type_code(value: str) -> str:
    return ensure_pattern(
        normalize_upper_code(value),
        _RESOLUTION_TYPE_CODE,
        field="code",
        message="El codigo de tipo de resolucion no tiene un formato valido.",
    )


def ensure_party_role_code(value: str) -> str:
    return ensure_pattern(
        normalize_upper_code(value),
        _PARTY_ROLE_CODE,
        field="code",
        message="El codigo de rol de parte no tiene un formato valido.",
    )


def ensure_tray_code(value: str) -> str:
    return ensure_pattern(
        normalize_upper_code(value),
        _TRAY_CODE,
        field="code",
        message="El codigo de bandeja no tiene un formato valido",
    )


def ensure_shelf_code(value: str) -> str:
    return ensure_pattern(
        normalize_upper_code(value),
        _SHELF_CODE,
        field="code",
        message="El codigo de anaquel no tiene un formato valido",
    )


def ensure_position_code(value: str) -> str:
    return ensure_pattern(
        normalize_upper_code(value),
        _POSITION_CODE,
        field="code",
        message="El codigo de posicion no tiene un formato valido.",
    )


def ensure_sequence_name(value: str) -> str:
    return ensure_pattern(
        normalize_lower_key(value),
        _SEQUENCE_NAME,
        field="sequence_name",
        message="El nombre de secuencia no tiene un formato valido.",
    )


def ensure_setting_key(value: str) -> str:
    return ensure_pattern(
        normalize_lower_key(value),
        _SETTING_KEY,
        field="key",
        message="La clave de configuracion no tiene un formato valido.",
    )


def validate_effective_range(effective_from: date | None, effective_to: date | None) -> None:
    if effective_from is not None and effective_to is not None and effective_to < effective_from:
        raise InvalidParameterError(
            "La fecha de fin de vigencia no puede ser anterior a la de inicio.",
            details={
                "effective_from": effective_from.isoformat(),
                "effective_to": effective_to.isoformat(),
            },
        )


def escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
