from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from judicial_archive.modules.administrative_documents.schemas import (
    AdministrativeDocumentInlineCreate,
)
from judicial_archive.modules.case_files.schemas import CaseFileInlineCreate

BoxTypeValue = Literal["EXPEDIENTES", "DOCUMENTOS_ADMINISTRATIVOS"]
ConfidentialityValue = Literal["INTERNAL", "RESTRICTED", "CONFIDENTIAL"]


class BoxSummaryOut(BaseModel):
    box_id: UUID
    visible_number: str
    box_type: str
    year: int
    court_id: UUID
    lifecycle_status: str
    custody_status: str
    location_precision: str
    location_state: str


class BoxLocationOut(BaseModel):
    box: BoxSummaryOut
    current_position_id: UUID | None
    version: int


class BoxLocationHistoryOut(BaseModel):
    id: UUID
    box_id: UUID
    movement_id: UUID | None
    from_position_id: UUID | None
    to_position_id: UUID | None
    from_custody_status: str | None
    to_custody_status: str
    from_location_precision: str | None
    to_location_precision: str
    reason: str
    source: str
    changed_at: datetime
    changed_by: UUID | None
    notes: str | None


class BoxCreate(BaseModel):
    court_id: UUID
    year: int = Field(ge=1, le=9999)
    box_type: BoxTypeValue
    description: str | None = Field(default=None, max_length=500)
    confidentiality: ConfidentialityValue = "INTERNAL"
    numbering_policy_id: UUID | None = None
    visible_number: str | None = Field(default=None, max_length=32)
    historical_exception: bool = False
    exception_reason: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _validate_historical_number(self) -> BoxCreate:
        if self.visible_number is not None and not self.historical_exception:
            raise ValueError("Un numero visible manual require historical_exception=true.")
        if self.historical_exception and not (self.exception_reason or "").strip():
            raise ValueError("La excepcion historica requiere exception_reason.")
        if self.visible_number is not None and not self.visible_number.strip():
            raise ValueError("El numero visible no puede estar vacio.")
        return self


class BoxUpdate(BaseModel):
    description: str | None = Field(default=None, max_length=500)
    confidentiality: ConfidentialityValue | None = None
    expected_version: int = Field(ge=1)


class BoxNumberCorrection(BaseModel):
    visible_number: str = Field(min_length=1, max_length=32)
    reason: str = Field(min_length=1, max_length=500)
    expected_version: int = Field(ge=1)


class BoxLifecycleRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)
    expected_version: int = Field(ge=1)


class BoxOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    visible_number: str
    court_id: UUID
    year: int
    box_type: str
    numbering_policy_id: UUID | None
    description: str | None
    confidentiality: str
    lifecycle_status: str
    custody_status: str
    current_position_id: UUID | None
    location_precision: str
    version: int
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime


class BoxNumberHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    box_id: UUID
    previous_number: str | None
    new_number: str
    reason: str
    changed_at: datetime
    changed_by: UUID | None


class BoxContentSummaryOut(BaseModel):
    box_id: UUID
    box_type: str
    case_file_count: int
    administrative_document_count: int
    total_count: int


class BoxWithContentCreate(BaseModel):
    box: BoxCreate
    case_files: list[CaseFileInlineCreate] = Field(default_factory=list)
    administrative_documents: list[AdministrativeDocumentInlineCreate] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_content_types(self) -> BoxWithContentCreate:
        has_cases = bool(self.case_files)
        has_docs = bool(self.administrative_documents)
        if has_cases and has_docs:
            raise ValueError("Una caja no puede mezclar expedientes y documentos administrativos.")
        if self.box.box_type == "EXPEDIENTES" and has_docs:
            raise ValueError("Una caja de expedientes no admite documentos administrativos.")
        if self.box.box_type == "DOCUMENTOS_ADMINISTRATIVOS" and has_cases:
            raise ValueError("Una caja administrativa no admite expedientes.")
        return self


class BoxWithContentOut(BaseModel):
    box: BoxOut
    case_file_ids: list[UUID] = Field(default_factory=list)
    administrative_document_ids: list[UUID] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
