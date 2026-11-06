from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

ConfidentialityValue = Literal["INTERNAL", "RESTRICTED", "CONFIDENTIAL"]
PrecisionValue = Literal["UNKNOWN", "YEAR", "MONTH", "DAY"]


class PersonCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=300)
    aliases: list[str] | None = None
    identification_type: str | None = Field(default=None, max_length=32)
    identification_number: str | None = Field(default=None, max_length=64)
    birth_year: int | None = Field(default=None, ge=1, le=9999)
    birth_month: int | None = Field(default=None, ge=1, le=12)
    birth_day: int | None = Field(default=None, ge=1, le=31)
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def _validate_birth_date(self) -> PersonCreate:
        if self.birth_month is not None and self.birth_year is None:
            raise ValueError("El mes de nacimiento requiere ano.")
        if self.birth_day is not None and self.birth_month is None:
            raise ValueError("El dia de nacimiento requiere mes.")
        return self


class PersonUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=300)
    aliases: list[str] | None = None
    identification_type: str | None = Field(default=None, max_length=32)
    identification_number: str | None = Field(default=None, max_length=64)
    notes: str | None = Field(default=None, max_length=2000)
    expected_version: int = Field(ge=1)


class PersonOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    display_name: str
    normalized_name: str
    aliases: list[str] | None
    identification_type: str | None
    identification_number: str | None
    birth_year: int | None
    birth_month: int | None
    birth_day: int | None
    notes: str | None
    version: int
    created_at: datetime
    updated_at: datetime


class CasePartyCreate(BaseModel):
    person_id: UUID
    party_role_id: UUID
    is_primary: bool = False
    notes: str | None = Field(default=None, max_length=1000)


class CasePartyWithPersonCreate(BaseModel):
    person: PersonCreate
    party_role_id: UUID
    is_primary: bool = False
    notes: str | None = Field(default=None, max_length=1000)


class CasePartyOut(BaseModel):
    id: UUID
    case_file_id: UUID
    person: PersonOut
    party_role_id: UUID
    party_role_code: str
    party_role_name: str
    is_primary: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime


class CaseFileInlineCreate(BaseModel):
    nuc: str = Field(min_length=1, max_length=100)
    year: int = Field(ge=1, le=9999)
    entry_precision: PrecisionValue = "UNKNOWN"
    entry_year: int | None = Field(default=None, ge=1, le=9999)
    entry_month: int | None = Field(default=None, ge=1, le=12)
    entry_day: int | None = Field(default=None, ge=1, le=31)
    sentence_precision: PrecisionValue = "UNKNOWN"
    sentence_year: int | None = Field(default=None, ge=1, le=9999)
    sentence_month: int | None = Field(default=None, ge=1, le=12)
    sentence_day: int | None = Field(default=None, ge=1, le=31)
    resolution_type_id: UUID | None = None
    resolution_number: str | None = Field(default=None, max_length=100)
    judge_name: str | None = Field(default=None, max_length=100)
    court_name_raw: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    confidentiality: ConfidentialityValue = "INTERNAL"
    source: str | None = Field(default=None, max_length=32)
    notes: str | None = Field(default=None, max_length=2000)
    historical_exception: bool = False
    exception_reason: str | None = Field(default=None, max_length=500)
    duplicate_override: bool = False
    duplicate_override_reason: str | None = Field(default=None, max_length=500)
    parties: list[CasePartyCreate] = Field(default_factory=list)


class CaseFileCreate(CaseFileInlineCreate):
    court_id: UUID
    box_id: UUID | None = None


class CaseFileUpdate(BaseModel):
    box_id: UUID | None = None
    change_reason: str | None = Field(default=None, max_length=500)
    entry_precision: PrecisionValue | None = None
    entry_year: int | None = Field(default=None, ge=1, le=9999)
    entry_month: int | None = Field(default=None, ge=1, le=12)
    entry_day: int | None = Field(default=None, ge=1, le=31)
    sentence_precision: PrecisionValue | None = None
    sentence_year: int | None = Field(default=None, ge=1, le=9999)
    sentence_month: int | None = Field(default=None, ge=1, le=12)
    sentence_day: int | None = Field(default=None, ge=1, le=31)
    resolution_type_id: UUID | None = None
    resolution_number: str | None = Field(default=None, max_length=100)
    judge_name: str | None = Field(default=None, max_length=200)
    court_name_raw: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    confidentiality: ConfidentialityValue | None = None
    notes: str | None = Field(default=None, max_length=2000)
    expected_version: int = Field(ge=1)


class CaseFileIdentifierCorrection(BaseModel):
    identifier_kind: Literal["NUC", "SENTENCE"]
    value: str = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=1, max_length=500)
    historical_exception: bool = False
    exception_reason: str | None = Field(default=None, max_length=500)
    expected_version: int = Field(ge=1)


class CaseFileRelocate(BaseModel):
    box_id: UUID
    reason: str = Field(min_length=1, max_length=500)
    expected_version: int = Field(ge=1)


class CaseFileLifecycleRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)
    expected_version: int = Field(ge=1)


class CaseFileDeleteRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)
    expected_version: int = Field(ge=1)


class CaseFileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    court_id: UUID
    box_id: UUID | None
    box_type: str
    nuc_raw: str
    nuc_normalized: str
    nuc_suffix5: str
    year: int
    entry_precision: str
    entry_year: int | None
    entry_month: int | None
    entry_day: int | None
    sentence_precision: str
    sentence_year: int | None
    sentence_month: int | None
    sentence_day: int | None
    resolution_type_id: UUID | None
    resolution_number: str | None
    judge_name: str | None
    court_name_raw: str | None
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


class CaseFileDetailOut(CaseFileOut):
    parties: list[CasePartyOut]
    warnings: list[str] = Field(default_factory=list)


class DuplicateCaseFileOut(BaseModel):
    id: UUID
    nuc_raw: str
    nuc_normalized: str
    nuc_suffix5: str
    court_id: UUID
    year: int
    box_id: UUID | None
    match_type: Literal["EXACT", "SUFFIX5", "SAME_YEAR"]
    verification_status: str


class DuplicatePersonOut(BaseModel):
    id: UUID
    display_name: str
    normalized_name: str
    identification_number: str | None
    match_type: Literal["IDENTIFICATION", "NAME"]
