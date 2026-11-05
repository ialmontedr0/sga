from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from judicial_archive.core.enums import (
    CustodyStatus,
    LocationPrecision,
    LocationState,
    PositionOccupancyState,
    PositionStatus,
)
from judicial_archive.modules.boxes.constants import ACTIVE_LOCATION_CUSTODY_STATUSES
from judicial_archive.modules.boxes.models import Box
from judicial_archive.modules.locations.models import Position, Shelf

__all__ = ["ACTIVE_LOCATION_CUSTODY_STATUSES"]

PositionOccupancyStateValue = Literal["EMPTY", "OCCUPIED", "BLOCKED", "RETIRED"]
UnlocatedLocationStateValue = Literal["UNASSIGNED", "PENDING_CONFIRMATION", "MISSING"]


@dataclass(frozen=True)
class CapacityMismatch:
    shelf_id: UUID
    shelf_code: str
    configured: int
    visible: int

    @property
    def delta(self) -> int:
        return self.visible - self.configured


@dataclass(frozen=True)
class OccupancyCounts:
    configured_capacity: int | None
    visible_capacity: int
    occupied_positions: int
    available_positions: int
    blocked_positions: int
    retired_positions: int
    occupancy_rate: float
    unlocated_boxes: int = 0
    pending_confirmation_boxes: int = 0
    in_transit_boxes: int = 0
    capacity_mismatches: tuple[CapacityMismatch, ...] = ()
    conflicts: tuple[str, ...] = ()

    @property
    def capacity_matches_configuration(self) -> bool:
        return not self.capacity_mismatches


def precision_for(custody_status: str, position_id: UUID | None) -> str:
    if position_id is None:
        return LocationPrecision.UNKNOWN.value
    if custody_status == CustodyStatus.IN_PLACE.value:
        return LocationPrecision.CONFIRMED.value
    return LocationPrecision.PENDING.value


def classify_location_state(box: Box) -> str:
    if box.custody_status == CustodyStatus.IN_PLACE.value:
        return LocationState.CONFIRMED.value
    if box.custody_status == CustodyStatus.PENDING_VERIFICATION.value:
        return LocationState.PENDING_CONFIRMATION.value
    if box.custody_status == CustodyStatus.IN_RECONCILIATION.value:
        return LocationState.IN_RECONCILIATION.value
    if box.custody_status == CustodyStatus.ON_LOAN.value:
        return LocationState.ON_LOAN.value
    if box.custody_status == CustodyStatus.IN_TRANSIT.value:
        return LocationState.IN_TRANSIT.value
    if box.custody_status == CustodyStatus.MISSING.value:
        return LocationState.MISSING.value
    return LocationState.UNASSIGNED.value


def is_operable(box: Box) -> bool:
    if box.lifecycle_status != "ACTIVE":
        return False
    return box.custody_status in {
        CustodyStatus.UNKNOWN.value,
        CustodyStatus.MISSING.value,
        CustodyStatus.IN_PLACE.value,
        CustodyStatus.PENDING_VERIFICATION.value,
    }


def position_occupancy_state(
    position: Position,
    box: Box | None,
) -> PositionOccupancyStateValue:
    if position.status == PositionStatus.RETIRED:
        return PositionOccupancyState.RETIRED.value
    if position.status == PositionStatus.BLOCKED:
        return PositionOccupancyState.BLOCKED.value
    if box is not None:
        return PositionOccupancyState.OCCUPIED.value
    return PositionOccupancyState.EMPTY.value


def classify_unlocated_state(box: Box) -> UnlocatedLocationStateValue:
    state = classify_location_state(box)
    if state == LocationState.MISSING.value:
        return "MISSING"
    if state == LocationState.PENDING_CONFIRMATION.value:
        return "PENDING_CONFIRMATION"
    return "UNASSIGNED"


def compute_shelf_occupancy(
    shelf: Shelf,
    positions: Sequence[Position],
    boxes_by_position: Mapping[UUID, Box],
) -> OccupancyCounts:
    visible = [position for position in positions if position.status != "RETIRED"]
    retired = len(positions) - len(visible)
    blocked = sum(1 for position in visible if position.status == PositionStatus.BLOCKED.value)
    occupied = 0
    conflicts: list[str] = []

    for position in visible:
        box = boxes_by_position.get(position.id)
        if box is None:
            continue
        if box.custody_status not in ACTIVE_LOCATION_CUSTODY_STATUSES:
            conflicts.append(
                f"La caja {box.visible_number} tiene posicion pero custodia {box.custody_status}."
            )
            continue
        if position.status != PositionStatus.AVAILABLE.value:
            conflicts.append(f"La posicion {position.code} esta {position.status} y tiene caja.")
            continue
        occupied += 1

    available = max(0, len(visible) - occupied - blocked)
    configured = shelf.capacity_positions
    mismatches: list[CapacityMismatch] = []
    if configured is not None and configured != len(visible):
        mismatches.append(
            CapacityMismatch(
                shelf_id=shelf.id,
                shelf_code=shelf.code,
                configured=configured,
                visible=len(visible),
            )
        )

    return OccupancyCounts(
        configured_capacity=configured,
        visible_capacity=len(visible),
        occupied_positions=occupied,
        available_positions=available,
        blocked_positions=blocked,
        retired_positions=retired,
        occupancy_rate=round(occupied / len(visible), 4) if visible else 0.0,
        capacity_mismatches=tuple(mismatches),
        conflicts=tuple(conflicts),
    )


def merge_counts(items: Sequence[OccupancyCounts]) -> OccupancyCounts:
    configured_values = [
        item.configured_capacity for item in items if item.configured_capacity is not None
    ]
    visible = sum(item.visible_capacity for item in items)
    occupied = sum(item.occupied_positions for item in items)
    return OccupancyCounts(
        configured_capacity=sum(configured_values) if configured_values else None,
        visible_capacity=visible,
        occupied_positions=occupied,
        available_positions=sum(item.available_positions for item in items),
        blocked_positions=sum(item.blocked_positions for item in items),
        retired_positions=sum(item.retired_positions for item in items),
        occupancy_rate=round(occupied / visible, 4) if visible else 0.0,
        unlocated_boxes=sum(item.unlocated_boxes for item in items),
        pending_confirmation_boxes=sum(item.pending_confirmation_boxes for item in items),
        in_transit_boxes=sum(item.in_transit_boxes for item in items),
        capacity_mismatches=tuple(
            mismatch for item in items for mismatch in item.capacity_mismatches
        ),
        conflicts=tuple(conflict for item in items for conflict in item.conflicts),
    )
