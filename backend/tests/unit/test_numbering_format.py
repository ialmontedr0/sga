from __future__ import annotations

import pytest

from judicial_archive.core.errors import InvalidParameterError
from judicial_archive.modules.courts.models import NumberingPolicy
from judicial_archive.modules.numbering.services import (
    format_visible_number,
    validate_format_capacity,
)


def _policy(**overrides: object) -> NumberingPolicy:
    values: dict[str, object] = {
        "code": "TEST",
        "scope": "GLOBAL",
        "sequence_name": "test_seq",
        "prefix": "C-",
        "suffix": None,
        "padding": 6,
        "start_value": 4402,
        "step": 1,
    }
    values.update(overrides)
    return NumberingPolicy(**values)


def test_format_visible_number_pads() -> None:
    assert format_visible_number(_policy(), 4402) == "C-004402"


def test_format_visible_number_uses_suffix() -> None:
    assert format_visible_number(_policy(prefix="A", suffix="-Z", padding=3), 7) == "A007-Z"


def test_format_visible_number_without_prefix_or_padding() -> None:
    assert format_visible_number(_policy(prefix=None, padding=0), 4402) == "4402"


def test_format_visible_number_rejects_non_positive_value() -> None:
    with pytest.raises(InvalidParameterError):
        format_visible_number(_policy(), 0)
    with pytest.raises(InvalidParameterError):
        format_visible_number(_policy(), -1)


def test_format_visible_number_rejects_too_long() -> None:
    with pytest.raises(InvalidParameterError):
        format_visible_number(_policy(prefix="X" * 32, padding=12), 10**11)


def test_validate_format_capacity_accepts_valid_policy() -> None:
    validate_format_capacity(_policy())


def test_validate_format_capacity_rejects_impossible_policy() -> None:
    with pytest.raises(InvalidParameterError):
        validate_format_capacity(_policy(prefix="X" * 32, padding=12))
