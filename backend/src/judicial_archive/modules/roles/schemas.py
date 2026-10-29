from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

RoleStatus = Literal["ACTIVE", "INACTIVE"]


class PermissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    description: str | None


class RoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    description: str | None
    is_system: bool
    status: str
    permissions: list[str] = Field(default_factory=list)


class RoleCreate(BaseModel):
    code: str = Field(min_length=2, max_length=64, pattern=r"^[A-Z][A-Z0-9_]{1,63}$")
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)


class RoleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    status: RoleStatus | None = None


class AssignPermissions(BaseModel):
    permission_codes: list[str] = Field(default_factory=list)


class PermissionCreate(BaseModel):
    code: str = Field(
        min_length=3,
        max_length=100,
        pattern=r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$",
    )
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=500)


class MessageResponse(BaseModel):
    message: str
