from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

NumberingScopeValue = Literal["GLOBAL", "COURT", "BOX_TYPE", "YEAR"]
BoxTypeValue = Literal["EXPEDIENTES", "DOCUMENTOS_ADMINISTRATIVOS"]


class NumberingPolicyCreate(BaseModel):
    code: str = Field(min_length=2, max_length=64)
    description: str | None = Field(default=None, max_length=500)
    scope: NumberingScopeValue
    court_id: UUID | None = None
    box_type: BoxTypeValue | None = None
    year: int | None = Field(default=None, ge=2000, le=2200)
    sequence_name: str = Field(min_length=3, max_length=63)
    prefix: str | None = Field(default=None, max_length=32)
    suffix: str | None = Field(default=None, max_length=32)
    padding: int = Field(default=0, ge=0, le=12)
    start_value: int = Field(ge=1)
    step: int = Field(default=1, ge=1, le=1000)
    reset_policy: Literal["NEVER"] = "NEVER"
    effective_from: date | None = None
    effective_to: date | None = None
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("code", "sequence_name")
    @classmethod
    def _code_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("El valor no puede estar vacio.")
        return value


class NumberingPolicyUpdate(BaseModel):
    description: str | None = Field(default=None, max_length=500)
    effective_to: date | None = None
    notes: str | None = Field(default=None, max_length=1000)


class NumberingPolicyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    description: str | None
    scope: str
    court_id: UUID | None
    box_type: str | None
    year: int | None
    sequence_name: str
    prefix: str | None
    suffix: str | None
    padding: int
    start_value: int
    step: int
    reset_policy: str
    is_active: bool
    effective_from: date
    effective_to: date | None
    notes: str | None
    version: int
    created_at: datetime
    updated_at: datetime


class NumberingPolicyStatusRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class NumberingPreviewOut(BaseModel):
    policy_id: UUID
    value: int
    formatted: str
