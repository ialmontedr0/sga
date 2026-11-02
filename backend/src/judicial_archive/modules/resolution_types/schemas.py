from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

CatalogStatusValue = Literal["ACTIVE", "INACTIVE"]


class ResolutionTypeCreate(BaseModel):
    code: str = Field(min_length=2, max_length=32)
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=500)

    @field_validator("code")
    @classmethod
    def _code_format(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized or not normalized[0].isalpha():
            raise ValueError("El codigo debe comenzar con una letra.")
        if not all(ch.isalnum() or ch == "_" for ch in normalized):
            raise ValueError("El codigo solo admite letras, digitos y guion bajo.")
        return normalized

    @field_validator("name")
    @classmethod
    def _name_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("El nombre no puede estar vacio.")
        return value


class ResolutionTypeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=500)


class ResolutionTypeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    description: str | None
    status: str
    version: int
    created_at: datetime
    updated_at: datetime


class ResolutionTypeStatusRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)
