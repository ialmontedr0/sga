from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    description: str | None
    is_system: bool
    status: str


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    email: EmailStr | None = None
    display_name: str = Field(min_length=1, max_length=160)
    password: str = Field(min_length=12, max_length=1024)
    role_codes: list[str] = []
    must_change_password: bool = True


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    display_name: str | None = Field(default=None, min_length=1, max_length=160)
    status: Literal["ACTIVE", "INACTIVE", "SUSPENDED", "LOCKED"] | None = None
    must_change_password: bool | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: str | None
    display_name: str
    status: str
    must_change_password: bool
    failed_login_count: int
    locked_until: datetime | None
    last_login_at: datetime | None
    created_at: datetime
    roles: list[str] = Field(default_factory=list)


class AssignRoles(BaseModel):
    role_codes: list[str] = Field(min_length=1)


class MessageResponse(BaseModel):
    message: str


class UserDetail(UserOut):
    permissions: list[str] = Field(default_factory=list)


class ResetPasswordRequest(BaseModel):
    new_password: str = Field(min_length=12, max_length=1024)
    must_change_password: bool = True
