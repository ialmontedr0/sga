from __future__ import annotations

import pytest

from judicial_archive.core.errors import InvalidParameterError
from judicial_archive.modules.case_files.validators import (
    identifier_kind_for_resolution,
    normalize_identifier,
    normalize_person_name,
)


def test_normalize_identifier_trims_uppercases_and_removes_whitespace() -> None:
    assert normalize_identifier("  nuc 2026  0001 ") == "NUC20260001"


def test_normalize_identifier_rejects_blank_values() -> None:
    with pytest.raises(InvalidParameterError):
        normalize_identifier("   ")


def test_normalize_person_name_removes_accents_and_spaces() -> None:
    assert normalize_person_name("  José   María  Núñez ") == "JOSEMARIANUNEZ"


def test_normalize_person_name_rejects_blank_values() -> None:
    with pytest.raises(InvalidParameterError):
        normalize_person_name("  ")


def test_identifier_kind_for_resolution_is_sentence() -> None:
    assert identifier_kind_for_resolution() == "SENTENCE"
