from __future__ import annotations

from types import SimpleNamespace
from typing import cast

import pytest

from judicial_archive.modules.boxes.models import Box
from judicial_archive.modules.locations.models import Position
from judicial_archive.modules.locations.occupancy import (
    classify_location_state,
    classify_unlocated_state,
    is_operable,
    position_occupancy_state,
)


@pytest.mark.parametrize(
    ("custody", "expected"),
    [
        ("IN_PLACE", "CONFIRMED"),
        ("PENDING_VERIFICATION", "PENDING_CONFIRMATION"),
        ("IN_RECONCILIATION", "IN_RECONCILIATION"),
        ("ON_LOAN", "ON_LOAN"),
        ("IN_TRANSIT", "IN_TRANSIT"),
        ("MISSING", "MISSING"),
        ("UNKNOWN", "UNASSIGNED"),
    ],
)
def test_classify_location_state(custody: str, expected: str) -> None:
    box = SimpleNamespace(custody_status=custody)
    assert classify_location_state(cast(Box, box)) == expected


@pytest.mark.parametrize(
    ("custody", "expected"),
    [
        ("PENDING_VERIFICATION", "PENDING_CONFIRMATION"),
        ("MISSING", "MISSING"),
        ("UNKNOWN", "UNASSIGNED"),
        ("ON_LOAN", "UNASSIGNED"),
    ],
)
def test_classify_unlocated_state(custody: str, expected: str) -> None:
    box = SimpleNamespace(custody_status=custody)
    assert classify_unlocated_state(cast(Box, box)) == expected


@pytest.mark.parametrize(
    ("lifecycle", "custody", "expected"),
    [
        ("ACTIVE", "UNKNOWN", True),
        ("ACTIVE", "MISSING", True),
        ("ACTIVE", "IN_PLACE", True),
        ("ACTIVE", "PENDING_VERIFICATION", True),
        ("ACTIVE", "ON_LOAN", False),
        ("ARCHIVED", "UNKNOWN", False),
    ],
)
def test_is_operable(lifecycle: str, custody: str, expected: bool) -> None:
    box = SimpleNamespace(lifecycle_status=lifecycle, custody_status=custody)
    assert is_operable(cast(Box, box)) is expected


@pytest.mark.parametrize(
    ("position_status", "has_box", "expected"),
    [
        ("AVAILABLE", False, "EMPTY"),
        ("AVAILABLE", True, "OCCUPIED"),
        ("BLOCKED", False, "BLOCKED"),
        ("BLOCKED", True, "BLOCKED"),
        ("RETIRED", False, "RETIRED"),
    ],
)
def test_position_occupancy_state(
    position_status: str,
    has_box: bool,
    expected: str,
) -> None:
    position = SimpleNamespace(status=position_status)
    box = SimpleNamespace() if has_box else None
    assert (
        position_occupancy_state(
            cast(Position, position),
            cast(Box | None, box),
        )
        == expected
    )
