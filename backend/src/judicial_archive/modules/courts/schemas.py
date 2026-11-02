from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

CourtStatusValue = Literal["ACTIVE", "INACTIVE"]


class CourtCreate(BaseModel):
    code_raw: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=200)
    court_type: str | None = Field(default=None, max_length=80)
    jurisdiction: str | None = Field(default=None, max_length=120)
    effective_from: date | None = None
    effective_to: date | None = None
    source: str | None = Field(default=None, max_length=64)
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("code_raw", "name")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("El valor no puede estar vacio.")
        return value

    @field_validator("court_type", "jurisdiction", "source", "notes")
    @classmethod
    def _optional_not_blank(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class CourtUpdate(BaseModel):
    code_raw: str | None | None = Field(default=None, min_length=1, max_length=32)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    court_type: str | None = Field(default=None, max_length=80)
    jurisdiction: str | None = Field(default=None, max_length=120)
    effective_from: date | None
    effective_to: date | None
    source: str | None = Field(default=None, max_length=64)
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("code_raw", "name")
    @classmethod
    def _not_blank_when_present(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("El valor no puede estar vacio.")
        return value


class CourtOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code_raw: str
    code_normalized: str
    name: str
    court_type: str | None
    jurisdiction: str | None
    status: str
    effective_from: date | None
    effective_to: date | None
    source: str | None
    notes: str | None
    version: int
    created_at: datetime
    updated_at: datetime


class CourtStatusRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)
