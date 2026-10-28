from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=1, max_length=1024)
    csrf_token: str | None = None


class UserMe(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: str | None
    display_name: str
    status: str
    must_change_password: bool
    roles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)


class SessionInfo(BaseModel):
    id: UUID
    created_at: datetime
    last_seen_at: datetime | None
    expires_at: datetime
    ip_address: str | None
    user_agent: str | None


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=1024)
    new_password: str = Field(min_length=12, max_length=1024)
    csrf_token: str | None = None


class MessageResponse(BaseModel):
    message: str
