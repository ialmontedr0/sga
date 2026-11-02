from __future__ import annotations

from datetime import date

import pytest

from judicial_archive.core.errors import InvalidParameterError
from judicial_archive.core.text import (
    clean_optional_text,
    ensure_area_code,
    ensure_party_role_code,
    ensure_position_code,
    ensure_resolution_type_code,
    ensure_sequence_name,
    ensure_setting_key,
    ensure_shelf_code,
    ensure_tray_code,
    escape_like,
    normalize_lower_key,
    normalize_upper_code,
    validate_effective_range,
)
from judicial_archive.modules.identifier_profiles.services import validate_identifier_pattern
from judicial_archive.modules.settings.validations import validate_setting_value


def test_normalize_upper_code() -> None:
    assert normalize_upper_code("  107-01 ") == "107-01"
    assert normalize_upper_code("zona-a") == "ZONA-A"


def test_normalize_lower_key() -> None:
    assert normalize_lower_key("  System.Timezone ") == "system.timezone"


def test_area_code_normalizes_and_validates() -> None:
    assert ensure_area_code(" zona-a ") == "ZONA-A"
    with pytest.raises(InvalidParameterError):
        ensure_area_code("1A")
    with pytest.raises(InvalidParameterError):
        ensure_area_code("A" * 17)


def test_resolution_type_code_normalizes_and_validates() -> None:
    assert ensure_resolution_type_code(" sentencia ") == "SENTENCIA"
    with pytest.raises(InvalidParameterError):
        ensure_resolution_type_code("SENTENCIA-1")


def test_party_role_code_normalizes_and_validates() -> None:
    assert ensure_party_role_code(" imputado ") == "IMPUTADO"
    with pytest.raises(InvalidParameterError):
        ensure_party_role_code("-IMPUTADO")


def test_physical_location_codes_normalize_and_validate() -> None:
    assert ensure_shelf_code("a1") == "A1"
    assert ensure_tray_code(" n-01 ") == "N-01"
    assert ensure_position_code(" p-001 ") == "P-001"

    with pytest.raises(InvalidParameterError):
        ensure_shelf_code("_A1")
    with pytest.raises(InvalidParameterError):
        ensure_tray_code("T" * 17)
    with pytest.raises(InvalidParameterError):
        ensure_position_code("P" * 33)


def test_sequence_name_rejects_hyphen_and_short_values() -> None:
    assert ensure_sequence_name(" Box_Seq ") == "box_seq"
    with pytest.raises(InvalidParameterError):
        ensure_sequence_name("box-seq")
    with pytest.raises(InvalidParameterError):
        ensure_sequence_name("ab")


def test_setting_key_rejects_spaces_and_short_values() -> None:
    assert ensure_setting_key(" System.Timezone ") == "system.timezone"
    with pytest.raises(InvalidParameterError):
        ensure_setting_key("System Timezone")
    with pytest.raises(InvalidParameterError):
        ensure_setting_key("a")


def test_effective_range_rejects_inverted_dates() -> None:
    with pytest.raises(InvalidParameterError):
        validate_effective_range(date(2026, 1, 2), date(2026, 1, 1))


def test_effective_range_accepts_open_or_equal_dates() -> None:
    validate_effective_range(None, date(2026, 1, 1))
    validate_effective_range(date(2026, 1, 1), None)
    validate_effective_range(date(2026, 1, 1), date(2026, 1, 1))


def test_clean_optional_text() -> None:
    assert clean_optional_text(None, max_length=10) is None
    assert clean_optional_text("   ", max_length=10) is None
    assert clean_optional_text("  texto  ", max_length=10) == "texto"
    with pytest.raises(InvalidParameterError):
        clean_optional_text("demasiado", max_length=3)


def test_escape_like() -> None:
    assert escape_like(r"a\b%c_d") == r"a\\b\%c\_d"


def test_strict_profile_requires_three_examples() -> None:
    with pytest.raises(InvalidParameterError):
        validate_identifier_pattern(
            pattern=r"^\d{5}$",
            examples=["00001", "00002"],
            rejects=["ABCDE"],
            strict=True,
            effective_from=date(2026, 1, 1),
            effective_to=None,
        )


def test_strict_profile_accepts_valid_examples() -> None:
    validate_identifier_pattern(
        pattern=r"^\d{5}$",
        examples=["00001", "00002", "00003"],
        rejects=["ABCDE"],
        strict=True,
        effective_from=date(2026, 1, 1),
        effective_to=None,
    )


def test_profile_rejects_nested_quantifier() -> None:
    with pytest.raises(InvalidParameterError):
        validate_identifier_pattern(
            pattern=r"^(a+)+$",
            examples=["aaa", "aaaa", "aaaaa"],
            rejects=[],
            strict=True,
            effective_from=date(2026, 1, 1),
            effective_to=None,
        )


def test_profile_rejects_numeric_backreference() -> None:
    with pytest.raises(InvalidParameterError):
        validate_identifier_pattern(
            pattern=r"(\d)\1",
            examples=["11", "22", "33"],
            rejects=[],
            strict=True,
            effective_from=date(2026, 1, 1),
            effective_to=None,
        )


def test_profile_rejects_invalid_regex() -> None:
    with pytest.raises(InvalidParameterError):
        validate_identifier_pattern(
            pattern=r"[",
            examples=[],
            rejects=[],
            strict=False,
            effective_from=date(2026, 1, 1),
            effective_to=None,
        )


def test_profile_rejects_accepted_reject_value() -> None:
    with pytest.raises(InvalidParameterError):
        validate_identifier_pattern(
            pattern=r"^\d{5}$",
            examples=["00001", "00002", "00003"],
            rejects=["12345"],
            strict=True,
            effective_from=date(2026, 1, 1),
            effective_to=None,
        )


def test_strict_profile_requires_pattern() -> None:
    with pytest.raises(InvalidParameterError):
        validate_identifier_pattern(
            pattern=None,
            examples=["00001", "00002", "00003"],
            rejects=[],
            strict=True,
            effective_from=date(2026, 1, 1),
            effective_to=None,
        )


def test_profile_rejects_inverted_effective_range() -> None:
    with pytest.raises(InvalidParameterError):
        validate_identifier_pattern(
            pattern=None,
            examples=None,
            rejects=None,
            strict=False,
            effective_from=date(2026, 2, 1),
            effective_to=date(2026, 1, 1),
        )


def test_setting_value_accepts_supported_types() -> None:
    validate_setting_value("system.timezone", "UTC", "STRING")
    validate_setting_value("retention.default_months", 60, "INTEGER")
    validate_setting_value("ui.dark_mode", True, "BOOLEAN")
    validate_setting_value("search.weights", {"nuc": 3}, "JSON")


def test_setting_value_rejects_sensitive_key() -> None:
    with pytest.raises(InvalidParameterError):
        validate_setting_value("db.password", "value", "STRING")


def test_setting_value_rejects_sensitive_value() -> None:
    with pytest.raises(InvalidParameterError):
        validate_setting_value("system.notice", "token=abc", "STRING")


def test_setting_value_rejects_type_mismatch() -> None:
    with pytest.raises(InvalidParameterError):
        validate_setting_value("retention.default_months", True, "INTEGER")
    with pytest.raises(InvalidParameterError):
        validate_setting_value("ui.dark_mode", "true", "BOOLEAN")
    with pytest.raises(InvalidParameterError):
        validate_setting_value("search.weights", "text", "JSON")
    with pytest.raises(InvalidParameterError):
        validate_setting_value("system.flag", 1, "FLOAT")


def test_setting_value_rejects_oversized_json() -> None:
    with pytest.raises(InvalidParameterError):
        validate_setting_value("search.payload", {"payload": "x" * 17_000}, "JSON")


def test_setting_timezone_must_exist() -> None:
    with pytest.raises(InvalidParameterError):
        validate_setting_value("system.timezone", "No/Existe", "STRING")
