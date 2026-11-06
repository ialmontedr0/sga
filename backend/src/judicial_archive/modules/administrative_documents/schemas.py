from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

ConfidentialityValue = Literal["INTERNAL", "RESTRICTED", "CONFIDENTIAL"]


class AdministrativeDocumentInlineCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    document_type: str | None = Field(default=None, max_length=80)
    document_year: int = Field(ge=1, le=9999)
    document_month: int | None = Field(default=None, ge=1, le=12)
    document_day: int | None = Field(default=None, ge=1, le=31)
    description: str | None = Field(default=None, max_length=1000)
    confidentiality: ConfidentialityValue = "INTERNAL"
    source: str | None = Field(default=None, max_length=32)
    notes: str | None = Field(default=None, max_length=2000)


class AdministrativeDocumentCreate(AdministrativeDocumentInlineCreate):
    box_id: UUID


class AdministrativeDocumentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    document_type: str | None = Field(default=None, max_length=80)
    document_year: int | None = Field(default=None, ge=1, le=9999)
    document_month: int | None = Field(default=None, ge=1, le=12)
    document_day: int | None = Field(default=None, ge=1, le=31)
    description: str | None = Field(default=None, max_length=1000)
    confidentiality: ConfidentialityValue | None = None
    source: str | None = Field(default=None, max_length=32)
    notes: str | None = Field(default=None, max_length=2000)
    expected_version: int = Field(ge=1)


class AdministrativeDocumentLifecycleRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)
    expected_version: int = Field(ge=1)


class AdministrativeDocumentDeleteRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)
    expected_version: int = Field(ge=1)


class AdministrativeDocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    box_id: UUID
    box_type: str
    title: str
    document_type: str | None
    document_year: int
    document_month: int | None
    document_day: int | None
    description: str | None
    verification_status: str
    confidentiality: str
    lifecycle_status: str
    source: str | None
    notes: str | None
    version: int
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class DuplicateAdministrativeDocumentOut(BaseModel):
    id: UUID
    box_id: UUID
    title: str
    document_year: int
    match_type: Literal["EXACT"]
