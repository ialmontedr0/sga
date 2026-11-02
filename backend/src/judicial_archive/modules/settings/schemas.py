from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

SettingType = Literal["STRING", "INTEGER", "BOOLEAN", "JSON"]


class SettingUpsert(BaseModel):
    value: Any
    value_type: SettingType
    description: str = Field(min_length=1, max_length=500)

    @field_validator("value")
    @classmethod
    def _value_not_none(cls, value: Any) -> Any:
        if value is None:
            raise ValueError("El valor no puede ser nulo.")
        return value


class SettingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    key: str
    value: Any
    value_type: str
    description: str
    updated_by: UUID | None
    created_at: datetime
    updated_at: datetime
