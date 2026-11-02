from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PartyRoleCreate(BaseModel):
    code: str = Field(min_length=2, max_length=64)
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=500)


class PartyRoleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=500)


class PartyRoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    description: str | None
    is_system: bool
    status: str
    version: int
    created_at: datetime
    updated_at: datetime


class PartyRoleStatusRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)
