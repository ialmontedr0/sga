from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    field_validator,
)

if TYPE_CHECKING:
    from judicial_archive.modules.boxes.schemas import BoxSummaryOut

AreaStatusValue = Literal["ACTIVE", "INACTIVE"]
ShelfStatusValue = Literal["ACTIVE", "INACTIVE"]
TrayStatusValue = Literal["ACTIVE", "INACTIVE"]
PositionStatusValue = Literal["AVAILABLE", "BLOCKED", "RETIRED"]


def _not_blank(value: str) -> str:
    if not value.strip():
        raise ValueError("El valor no puede estar vacio.")
    return value


class AreaCreate(BaseModel):
    code: str = Field(min_length=1, max_length=16)
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)

    @field_validator("code", "name")
    @classmethod
    def _required_text(cls, value: str) -> str:
        return _not_blank(value)


class AreaUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=16)
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)


class AreaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    description: str | None
    status: str
    version: int
    created_at: datetime
    updated_at: datetime


class AreaStatusRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class CapacityTarget(BaseModel):
    levels: int = Field(ge=1, le=5000)
    positions_per_level: int = Field(ge=1, le=5000)

    @field_validator("positions_per_level")
    @classmethod
    def _max_total(cls, value: int, info: ValidationInfo) -> int:

        levels = info.data.get("levels", 1)

        if levels * value > 5000:
            raise ValueError("La capacidad total no puede superar 5000 posiciones.")
        return value


class ShelfCreate(BaseModel):
    area_id: UUID
    code: str = Field(min_length=1, max_length=16)
    name: str | None = Field(default=None, max_length=120)
    levels: int | None = Field(default=None, ge=1, le=5000)
    positions_per_level: int | None = Field(default=None, ge=1, le=5000)
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("code")
    @classmethod
    def _code_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("positions_per_level")
    @classmethod
    def _pair_and_total(cls, value: int | None, info: ValidationInfo) -> int | None:
        levels = info.data.get("levels")

        if (levels is None) != (value is None):
            raise ValueError("levels y positions_per_level deben enviarse juntos.")

        if levels is not None and value is not None and levels * value > 5000:
            raise ValueError("La capacidad total no puede superar 5000 posiciones.")
        return value


class ShelfUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=16)
    name: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=1000)


class ShelfOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    area_id: UUID
    code: str
    name: str | None
    levels: int | None
    positions_per_level: int | None
    capacity_positions: int | None
    status: str
    notes: str | None
    version: int
    created_at: datetime
    updated_at: datetime


class ShelfStatusRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class CapacityApplyRequest(CapacityTarget):
    expected_version: int = Field(ge=1)


class CapacityConflictOut(BaseModel):
    level: str
    code: str
    message: str


class CapacityPlanOut(BaseModel):
    shelf_id: UUID
    target_levels: int
    target_positions_per_level: int
    target_total: int
    current_total: int
    trays_to_create: int
    trays_to_reactivate: int
    trays_to_retire: int
    positions_to_create: int
    positions_to_reactivate: int
    positions_to_retire: int
    conflicts: list[CapacityConflictOut]
    can_apply: bool


class CapacityApplyOut(BaseModel):
    shelf: ShelfOut
    plan: CapacityPlanOut


class TrayCreate(BaseModel):
    shelf_id: UUID
    code: str = Field(min_length=1, max_length=16)
    name: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("code")
    @classmethod
    def _code_not_blank(cls, value: str) -> str:
        return _not_blank(value)


class TrayUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=16)
    name: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=1000)


class TrayOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    shelf_id: UUID
    code: str
    name: str | None
    position_count: int | None
    status: str
    notes: str | None
    version: int
    created_at: datetime
    updated_at: datetime


class TrayStatusRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class PositionCreate(BaseModel):
    tray_id: UUID
    code: str = Field(min_length=1, max_length=32)
    label: str = Field(min_length=1, max_length=80)
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("code", "label")
    @classmethod
    def _required_text(cls, value: str) -> str:
        return _not_blank(value)


class PositionUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=32)
    label: str | None = Field(default=None, min_length=1, max_length=80)
    notes: str | None = Field(default=None, max_length=1000)


class PositionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tray_id: UUID
    code: str
    label: str
    status: str
    notes: str | None
    version: int
    created_at: datetime
    updated_at: datetime


class PositionRetireRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class BoxTypeOut(BaseModel):
    value: str
    label: str


class AreaPathOut(BaseModel):
    id: UUID
    code: str
    name: str


class ShelfPathOut(BaseModel):
    id: UUID
    code: str
    name: str | None


class TrayPathOut(BaseModel):
    id: UUID
    code: str
    name: str | None


class PositionPathOut(BaseModel):
    position_id: UUID
    position_code: str
    label: str
    position_status: str
    tray: TrayPathOut
    shelf: ShelfPathOut
    area: AreaPathOut


class CapacityMismatchOut(BaseModel):
    shelf_id: UUID
    shelf_code: str
    configured: int
    visible: int
    delta: int


class OccupancySummaryOut(BaseModel):
    scope: Literal["GLOBAL", "AREA", "SHELF", "TRAY"]
    scope_id: UUID | None
    configured_capacity: int | None
    visible_capacity: int
    occupied_positions: int
    available_positions: int
    blocked_positions: int
    retired_positions: int
    occupancy_rate: float
    unlocated_boxes: int
    pending_confirmation_boxes: int
    in_transit_boxes: int
    capacity_matches_configuration: bool
    capacity_mismatches: list[CapacityMismatchOut]
    conflicts: list[str]


class PositionOccupancyOut(BaseModel):
    position: PositionPathOut
    state: Literal["EMPTY", "OCCUPIED", "BLOCKED", "RETIRED"]
    box: BoxSummaryOut | None
    block_id: UUID | None


class LocationPlanPositionOut(PositionOccupancyOut):
    pass


class LocationPlanTrayOut(BaseModel):
    tray: TrayPathOut
    visible_capacity: int
    occupied_positions: int
    positions: list[LocationPlanPositionOut] | None


class LocationPlanShelfOut(BaseModel):
    shelf: ShelfPathOut
    configured_capacity: int | None
    visible_capacity: int
    occupied_positions: int
    available_positions: int
    blocked_positions: int
    trays: list[LocationPlanTrayOut]


class LocationPlanOut(BaseModel):
    area: AreaPathOut | None
    shelves: list[LocationPlanShelfOut]
    summary: OccupancySummaryOut


class UnlocatedBoxOut(BaseModel):
    box: BoxSummaryOut
    location_state: Literal["UNASSIGNED", "PENDING_CONFIRMATION", "MISSING"]
    last_movement_at: datetime | None


class ScanBoxOut(BaseModel):
    kind: Literal["BOX"]
    box: BoxSummaryOut
    current_position: PositionPathOut | None
    location_state: str
    operable: bool
    message: str


class ScanPositionOut(BaseModel):
    kind: Literal["POSITION"]
    position: PositionPathOut
    state: Literal["EMPTY", "OCCUPIED", "BLOCKED", "RETIRED"]
    box: BoxSummaryOut | None
    message: str


class ScanUnregisteredOut(BaseModel):
    kind: Literal["UNREGISTERED_BOX"]
    box_number: str
    message: str


class ScanResponse(BaseModel):
    kind: Literal["BOX", "POSITION", "UNREGISTERED_BOX"]
    box: BoxSummaryOut | None = None
    position: PositionPathOut | None = None
    position_state: Literal["EMPTY", "OCCUPIED", "BLOCKED", "RETIRED"] | None = None
    box_number: str | None = None
    current_position: PositionPathOut | None = None
    location_state: str | None = None
    operable: bool | None = None
    message: str


class PositionBlockCreate(BaseModel):
    shelf_id: UUID
    start_position_id: UUID
    end_position_id: UUID
    reason: str = Field(min_length=1, max_length=500)
    notes: str | None = Field(default=None, max_length=1000)
    expected_version: int = Field(ge=1)

    @field_validator("reason")
    @classmethod
    def _reason_not_blank(cls, value: str) -> str:
        return _not_blank(value)


class PositionBlockCancel(BaseModel):
    reason: str = Field(min_length=1, max_length=500)
    expected_version: int = Field(ge=1)

    @field_validator("reason")
    @classmethod
    def _reason_not_blank(cls, value: str) -> str:
        return _not_blank(value)


class PositionBlockOut(BaseModel):
    id: UUID
    shelf_id: UUID
    start_position: PositionPathOut
    end_position: PositionPathOut
    first_position_number: int
    last_position_number: int
    reason: str
    notes: str | None
    blocked_by: UUID | None
    cancelled_at: datetime | None
    cancelled_by: UUID | None
    cancellation_reason: str | None
    created_at: datetime


class OccupancyReportRowOut(BaseModel):
    area_code: str
    area_name: str
    shelf_code: str
    shelf_name: str | None
    configured_capacity: int | None
    visible_capacity: int
    occupied_positions: int
    available_positions: int
    blocked_positions: int
    retired_positions: int
    occupancy_rate: float
    capacity_matches: bool


class OccupancyReportOut(BaseModel):
    generated_at: datetime
    area_id: UUID | None
    shelf_id: UUID | None
    totals: OccupancySummaryOut
    rows: list[OccupancyReportRowOut]


from judicial_archive.modules.boxes.schemas import BoxSummaryOut  # noqa: E402

PositionOccupancyOut.model_rebuild()
UnlocatedBoxOut.model_rebuild()
ScanBoxOut.model_rebuild()
ScanPositionOut.model_rebuild()
ScanResponse.model_rebuild()
