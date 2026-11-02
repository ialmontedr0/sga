from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

IdentifierKindValue = Literal["NUC", "PROCESS_NUMBER", "SENTENCE"]


class IdentifierProfileCreate(BaseModel):
    court_id: UUID
    identifier_kind: IdentifierKindValue
    pattern: str | None = Field(default=None, max_length=255)
    tokens: dict[str, Any] | None = None
    examples: list[str] | None = Field(default=None, max_length=50)
    rejects: list[str] | None = Field(default=None, max_length=50)
    strict: bool = False
    effective_from: date | None = None
    effective_to: date | None = None
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("pattern")
    @classmethod
    def _pattern_not_blank(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None

    @field_validator("examples", "rejects")
    @classmethod
    def _values_not_blank(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        cleaned = [item.strip() for item in value]
        if any(not item for item in cleaned):
            raise ValueError("Los ejemplos y rechazos no pueden estar vacios.")
        return cleaned


class IdentifierProfileReplace(BaseModel):
    pattern: str | None = Field(default=None, max_length=255)
    tokens: dict[str, Any] | None = None
    examples: list[str] | None = Field(default=None, max_length=50)
    rejects: list[str] | None = Field(default=None, max_length=50)
    strict: bool = False
    effective_from: date
    notes: str | None = Field(default=None, max_length=1000)


class IdentifierProfileUpdate(BaseModel):
    notes: str | None = Field(default=None, max_length=1000)
    effective_to: date | None = None


class IdentifierProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    court_id: UUID
    identifier_kind: str
    pattern: str | None
    tokens: dict[str, Any] | None
    examples: list[Any] | None
    rejects: list[Any] | None
    strict: bool
    is_active: bool
    effective_from: date
    effective_to: date | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class IdentifierProfileStatusRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)
