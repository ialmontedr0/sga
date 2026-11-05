from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class BoxSummaryOut(BaseModel):
    box_id: UUID
    visible_number: str
    box_type: str
    year: int
    court_id: UUID
    lifecycle_status: str
    custody_status: str
    location_precision: str
    location_state: str


class BoxLocationOut(BaseModel):
    box: BoxSummaryOut
    current_position_id: UUID | None
    version: int


class BoxLocationHistoryOut(BaseModel):
    id: UUID
    box_id: UUID
    movement_id: UUID | None
    from_position_id: UUID | None
    to_position_id: UUID | None
    from_custody_status: str | None
    to_custody_status: str
    from_location_precision: str | None
    to_location_precision: str
    reason: str
    source: str
    changed_at: datetime
    changed_by: UUID | None
    notes: str | None
