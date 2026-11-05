from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from uuid import uuid4

from judicial_archive.modules.locations.occupancy import (
    compute_shelf_occupancy,
    merge_counts,
)


def _shelf(*, capacity: int | None = None) -> Any:
    return SimpleNamespace(
        id=uuid4(),
        code="S1",
        capacity_positions=capacity,
    )


def _position(*, status: str = "AVAILABLE", code: str = "P1") -> Any:
    return SimpleNamespace(id=uuid4(), status=status, code=code)


def _box(*, custody: str = "IN_PLACE", number: str = "B-1") -> Any:
    return SimpleNamespace(custody_status=custody, visible_number=number)


def test_empty_shelf_has_zero_occupancy() -> None:
    shelf = _shelf(capacity=3)
    positions = [_position(code=f"P{i}") for i in range(1, 4)]

    counts = compute_shelf_occupancy(shelf, positions, {})

    assert counts.configured_capacity == 3
    assert counts.visible_capacity == 3
    assert counts.occupied_positions == 0
    assert counts.available_positions == 3
    assert counts.occupancy_rate == 0.0
    assert counts.capacity_matches_configuration is True


def test_occupied_and_blocked_positions_are_counted_once() -> None:
    shelf = _shelf(capacity=3)
    occupied = _position(code="P1")
    blocked = _position(status="BLOCKED", code="P2")
    empty = _position(code="P3")

    counts = compute_shelf_occupancy(
        shelf,
        [occupied, blocked, empty],
        {occupied.id: _box()},
    )

    assert counts.occupied_positions == 1
    assert counts.blocked_positions == 1
    assert counts.available_positions == 1
    assert counts.occupancy_rate == 0.3333


def test_retired_positions_are_not_visible_capacity() -> None:
    shelf = _shelf(capacity=3)
    positions = [
        _position(code="P1"),
        _position(code="P2"),
        _position(status="RETIRED", code="P3"),
    ]

    counts = compute_shelf_occupancy(shelf, positions, {})

    assert counts.visible_capacity == 2
    assert counts.retired_positions == 1
    assert counts.capacity_mismatches[0].delta == -1


def test_box_in_blocked_position_is_a_conflict_not_occupied() -> None:
    shelf = _shelf(capacity=1)
    position = _position(status="BLOCKED", code="P1")

    counts = compute_shelf_occupancy(
        shelf,
        [position],
        {position.id: _box(number="B-9")},
    )

    assert counts.occupied_positions == 0
    assert counts.blocked_positions == 1
    assert counts.conflicts
    assert "P1" in counts.conflicts[0]


def test_box_with_invalid_custody_is_a_conflict() -> None:
    shelf = _shelf(capacity=1)
    position = _position(code="P1")

    counts = compute_shelf_occupancy(
        shelf,
        [position],
        {position.id: _box(custody="ON_LOAN")},
    )

    assert counts.occupied_positions == 0
    assert counts.conflicts
    assert "ON_LOAN" in counts.conflicts[0]


def test_merge_counts_keeps_global_rate_and_mismatches() -> None:
    first = compute_shelf_occupancy(
        _shelf(capacity=2),
        [_position(code="P1"), _position(code="P2")],
        {},
    )
    second = compute_shelf_occupancy(
        _shelf(capacity=3),
        [_position(code="P1")],
        {},
    )

    merged = merge_counts([first, second])

    assert merged.configured_capacity == 5
    assert merged.visible_capacity == 3
    assert merged.available_positions == 3
    assert len(merged.capacity_mismatches) == 1
