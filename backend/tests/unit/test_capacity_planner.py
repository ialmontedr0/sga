from __future__ import annotations

from uuid import uuid4

import pytest

from judicial_archive.core.errors import InvalidParameterError
from judicial_archive.modules.locations.capacity import build_capacity_plan
from judicial_archive.modules.locations.models import Position, Tray


def _tray(code: str = "N01", *, status: str = "ACTIVE") -> Tray:
    return Tray(
        id=uuid4(),
        shelf_id=uuid4(),
        code=code,
        status=status,
        position_count=None,
    )


def _position(tray: Tray, code: str, *, status: str = "AVAILABLE") -> Position:
    return Position(
        id=uuid4(),
        tray_id=tray.id,
        code=code,
        label=f"Nivel {tray.code} - Posicion {code}",
        status=status,
    )


def test_increase_capacity_creates_trays_and_positions() -> None:
    plan = build_capacity_plan(
        shelf_id=uuid4(),
        target_levels=2,
        positions_per_level=3,
        trays=[],
        positions_by_tray={},
        occupied_position_ids=set(),
    )

    assert plan.can_apply
    assert plan.target_total == 6
    assert plan.current_total == 0
    assert plan.trays_to_create == 2
    assert plan.positions_to_create == 6
    assert [action.code for action in plan.tray_actions] == ["N01", "N02"]


def test_retire_occupied_position_conflicts() -> None:
    tray = _tray()
    p1 = _position(tray, "P001")
    p2 = _position(tray, "P002")
    plan = build_capacity_plan(
        shelf_id=uuid4(),
        target_levels=1,
        positions_per_level=1,
        trays=[tray],
        positions_by_tray={tray.id: [p1, p2]},
        occupied_position_ids={p2.id},
    )

    assert not plan.can_apply
    assert plan.conflicts[0].code == "P002"
    assert plan.positions_to_retire == 0


def test_retire_blocked_position_conflicts() -> None:
    tray = _tray()
    p1 = _position(tray, "P001")
    p2 = _position(tray, "P002", status="BLOCKED")
    plan = build_capacity_plan(
        shelf_id=uuid4(),
        target_levels=1,
        positions_per_level=1,
        trays=[tray],
        positions_by_tray={tray.id: [p1, p2]},
        occupied_position_ids=set(),
    )

    assert not plan.can_apply
    assert plan.conflicts[0].code == "P002"
    assert "bloqueada" in plan.conflicts[0].message.lower()


def test_inactive_tray_is_reactivated() -> None:
    tray = _tray(status="INACTIVE")
    positions = [_position(tray, "P001"), _position(tray, "P002")]
    plan = build_capacity_plan(
        shelf_id=uuid4(),
        target_levels=1,
        positions_per_level=2,
        trays=[tray],
        positions_by_tray={tray.id: positions},
        occupied_position_ids=set(),
    )

    assert plan.can_apply
    assert plan.trays_to_reactivate == 1
    assert plan.tray_actions[0].action == "reactivate"
    assert plan.positions_to_create == 0


def test_retired_positions_are_reactivated_before_creating_new_ones() -> None:
    tray = _tray()
    p1 = _position(tray, "P001")
    p2 = _position(tray, "P002", status="RETIRED")
    plan = build_capacity_plan(
        shelf_id=uuid4(),
        target_levels=1,
        positions_per_level=2,
        trays=[tray],
        positions_by_tray={tray.id: [p1, p2]},
        occupied_position_ids=set(),
    )

    assert plan.can_apply
    assert plan.positions_to_reactivate == 1
    assert plan.positions_to_create == 0
    assert plan.tray_actions[0].reactivate_position_ids == (p2.id,)


def test_new_tray_code_avoids_existing_codes() -> None:
    tray = _tray("N01")
    p1 = _position(tray, "P001")
    plan = build_capacity_plan(
        shelf_id=uuid4(),
        target_levels=2,
        positions_per_level=1,
        trays=[tray],
        positions_by_tray={tray.id: [p1]},
        occupied_position_ids=set(),
    )

    assert plan.can_apply
    assert plan.trays_to_create == 1
    assert plan.tray_actions[-1].action == "create"
    assert plan.tray_actions[-1].code == "N02"


def test_new_position_codes_avoid_existing_codes() -> None:
    tray = _tray("N01")
    p1 = _position(tray, "P001")
    plan = build_capacity_plan(
        shelf_id=uuid4(),
        target_levels=1,
        positions_per_level=3,
        trays=[tray],
        positions_by_tray={tray.id: [p1]},
        occupied_position_ids=set(),
    )

    assert plan.can_apply
    assert plan.positions_to_create == 2
    assert [item.code for item in plan.tray_actions[0].new_positions] == ["P002", "P003"]


def test_unselected_tray_is_retired() -> None:
    t1 = _tray("N01")
    t2 = _tray("N02")
    p1 = _position(t1, "P001")
    p2 = _position(t2, "P001")
    plan = build_capacity_plan(
        shelf_id=uuid4(),
        target_levels=1,
        positions_per_level=1,
        trays=[t1, t2],
        positions_by_tray={t1.id: [p1], t2.id: [p2]},
        occupied_position_ids=set(),
    )

    assert plan.can_apply
    assert plan.trays_to_retire == 1
    assert plan.positions_to_retire == 1
    retire = next(action for action in plan.tray_actions if action.action == "retire")
    assert retire.code == "N02"
    assert retire.retire_position_ids == (p2.id,)


def test_unselected_tray_with_occupied_position_conflicts() -> None:
    t1 = _tray("N01")
    t2 = _tray("N02")
    p1 = _position(t1, "P001")
    p2 = _position(t2, "P001")
    plan = build_capacity_plan(
        shelf_id=uuid4(),
        target_levels=1,
        positions_per_level=1,
        trays=[t1, t2],
        positions_by_tray={t1.id: [p1], t2.id: [p2]},
        occupied_position_ids={p2.id},
    )

    assert not plan.can_apply
    assert plan.conflicts[0].code == "P001"
    assert "retirar la bandeja" in plan.conflicts[0].message.lower()


def test_capacity_must_be_positive() -> None:
    with pytest.raises(InvalidParameterError):
        build_capacity_plan(
            shelf_id=uuid4(),
            target_levels=0,
            positions_per_level=1,
            trays=[],
            positions_by_tray={},
            occupied_position_ids=set(),
        )
    with pytest.raises(InvalidParameterError):
        build_capacity_plan(
            shelf_id=uuid4(),
            target_levels=1,
            positions_per_level=0,
            trays=[],
            positions_by_tray={},
            occupied_position_ids=set(),
        )


def test_capacity_above_maximum_is_rejected() -> None:
    with pytest.raises(InvalidParameterError):
        build_capacity_plan(
            shelf_id=uuid4(),
            target_levels=5001,
            positions_per_level=1,
            trays=[],
            positions_by_tray={},
            occupied_position_ids=set(),
        )


def test_capacity_at_maximum_is_accepted() -> None:
    plan = build_capacity_plan(
        shelf_id=uuid4(),
        target_levels=5000,
        positions_per_level=1,
        trays=[],
        positions_by_tray={},
        occupied_position_ids=set(),
    )

    assert plan.can_apply
    assert plan.target_total == 5000
    assert plan.trays_to_create == 5000
    assert plan.positions_to_create == 5000
