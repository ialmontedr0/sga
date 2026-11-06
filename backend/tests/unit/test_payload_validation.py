from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from judicial_archive.modules.administrative_documents.schemas import (
    AdministrativeDocumentInlineCreate,
)
from judicial_archive.modules.boxes.schemas import BoxCreate, BoxWithContentCreate
from judicial_archive.modules.case_files.schemas import (
    CaseFileInlineCreate,
    PersonCreate,
)


def test_manual_box_number_requires_historical_exception() -> None:
    with pytest.raises(ValidationError):
        BoxCreate(
            court_id=uuid4(),
            year=2026,
            box_type="EXPEDIENTES",
            visible_number="C-0001",
        )


def test_historical_exception_requires_reason() -> None:
    with pytest.raises(ValidationError):
        BoxCreate(
            court_id=uuid4(),
            year=2026,
            box_type="EXPEDIENTES",
            visible_number="C-0001",
            historical_exception=True,
        )


def test_historical_box_number_with_reason_is_valid() -> None:
    box = BoxCreate(
        court_id=uuid4(),
        year=2026,
        box_type="EXPEDIENTES",
        visible_number="C-0001",
        historical_exception=True,
        exception_reason="Caja heredada del inventario anterior.",
    )

    assert box.visible_number == "C-0001"


def test_box_with_content_rejects_mixed_content() -> None:
    with pytest.raises(ValidationError):
        BoxWithContentCreate(
            box=BoxCreate(court_id=uuid4(), year=2026, box_type="EXPEDIENTES"),
            case_files=[CaseFileInlineCreate(nuc="NUC-2026-0001", year=2026)],
            administrative_documents=[
                AdministrativeDocumentInlineCreate(title="Oficio", document_year=2026)
            ],
        )


def test_box_with_content_rejects_documents_in_case_box() -> None:
    with pytest.raises(ValidationError):
        BoxWithContentCreate(
            box=BoxCreate(court_id=uuid4(), year=2026, box_type="EXPEDIENTES"),
            administrative_documents=[
                AdministrativeDocumentInlineCreate(title="Oficio", document_year=2026)
            ],
        )


def test_box_with_content_rejects_cases_in_administrative_box() -> None:
    with pytest.raises(ValidationError):
        BoxWithContentCreate(
            box=BoxCreate(
                court_id=uuid4(),
                year=2026,
                box_type="DOCUMENTOS_ADMINISTRATIVOS",
            ),
            case_files=[CaseFileInlineCreate(nuc="NUC-2026-0001", year=2026)],
        )


def test_box_with_content_accepts_matching_inline_content() -> None:
    payload = BoxWithContentCreate(
        box=BoxCreate(court_id=uuid4(), year=2026, box_type="EXPEDIENTES"),
        case_files=[CaseFileInlineCreate(nuc="NUC-2026-0001", year=2026)],
    )

    assert len(payload.case_files) == 1
    assert payload.case_files[0].nuc == "NUC-2026-0001"


def test_person_birth_month_requires_year() -> None:
    with pytest.raises(ValidationError):
        PersonCreate(display_name="Persona", birth_month=1)


def test_person_birth_day_requires_month() -> None:
    with pytest.raises(ValidationError):
        PersonCreate(display_name="Persona", birth_year=1990, birth_day=1)


def test_person_birth_date_is_valid_with_full_date() -> None:
    person = PersonCreate(
        display_name="Persona",
        birth_year=1990,
        birth_month=1,
        birth_day=15,
    )

    assert person.birth_day == 15
