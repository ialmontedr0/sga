from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from judicial_archive.core.enums import TransferMode
from judicial_archive.modules.boxes.schemas import BoxLocationHistoryOut, BoxSummaryOut
from judicial_archive.modules.locations.schemas import PositionPathOut


def _not_blank(value: str) -> str:
    if not value.strip():
        raise ValueError("El valor no puede estar vacio")
    return value


class AssignRequest(BaseModel):
    position_id: UUID
    confirmed: bool = False
    reason: str = Field(min_length=1, max_length=500)
    notes: str | None = Field(default=None, max_length=1000)
    expected_version: int = Field(ge=1)

    @field_validator("reason")
    @classmethod
    def _reason_not_blank(cls, value: str) -> str:
        return _not_blank(value)


class UnassignRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)
    notes: str | None = Field(default=None, max_length=1000)
    expected_version: int = Field(ge=1)

    @field_validator("reason")
    @classmethod
    def _reason_not_blank(cls, value: str) -> str:
        return _not_blank(value)


class TransferRequest(BaseModel):
    to_position_id: UUID
    mode: TransferMode = TransferMode.IMMEDIATE
    confirmed: bool = False
    reason: str = Field(min_length=1, max_length=500)
    notes: str | None = Field(default=None, max_length=1000)
    expected_version: int = Field(ge=1)

    @field_validator("reason")
    @classmethod
    def _reason_not_blank(cls, value: str) -> str:
        return _not_blank(value)


class ConfirmRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)
    notes: str | None = Field(default=None, max_length=1000)
    expected_version: int = Field(ge=1)

    @field_validator("reason")
    @classmethod
    def _reason_not_blank(cls, value: str) -> str:
        return _not_blank(value)


class CompleteMovementRequest(BaseModel):
    confirmed: bool = True
    reason: str = Field(min_length=1, max_length=500)
    notes: str | None = Field(default=None, max_length=1000)
    expected_version: int = Field(ge=1)

    @field_validator("reason")
    @classmethod
    def _reason_not_blank(cls, value: str) -> str:
        return _not_blank(value)


class CancelMovementRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)
    notes: str | None = Field(default=None, max_length=1000)
    expected_version: int = Field(ge=1)

    @field_validator("reason")
    @classmethod
    def _reason_not_blank(cls, value: str) -> str:
        return _not_blank(value)


class MovementOut(BaseModel):
    id: UUID
    box_id: UUID
    movement_type: str
    movement_status: str
    from_position: PositionPathOut | None
    to_position: PositionPathOut | None
    occurred_at: datetime
    completed_at: datetime | None
    cancelled_at: datetime | None
    reason: str
    performed_by: UUID | None
    notes: str | None
    version: int


class BoxLocationDetailOut(BaseModel):
    box: BoxSummaryOut
    current_position: PositionPathOut | None
    open_movement: MovementOut | None
    last_movement: MovementOut | None
    history_count: int
    operable: bool
    version: int


class LocationMutationOut(BaseModel):
    box: BoxLocationDetailOut
    movement: MovementOut | None
    history: BoxLocationHistoryOut
