from __future__ import annotations

from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from judicial_archive.modules.audit.models import AuditEvent
from judicial_archive.modules.boxes.models import BoxNumberHistory
from judicial_archive.modules.case_files.models import CaseFileIdentifierHistory
from tests.integration.auth_helpers import (
    ADMIN_PASSWORD,
    ADMIN_USERNAME,
    csrf_headers,
    login,
)
from tests.integration.b7_helpers import active_court_id, create_box, create_case_file

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_identifier_correction_records_history_and_audit(
    seeded_api_client: TestClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    client = seeded_api_client
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    court_id = active_court_id(client)
    box = create_box(client, court_id=court_id)
    case_file = create_case_file(
        client,
        court_id=court_id,
        box_id=box["id"],
        nuc="NUC-2026-3001",
    )

    response = client.post(
        f"/api/v1/case-files/{case_file['id']}/identifiers/correct",
        json={
            "identifier_kind": "NUC",
            "value": "NUC-2026-3002",
            "reason": "Correccion de NUC de prueba.",
            "expected_version": 1,
        },
        headers=csrf_headers(client),
    )

    assert response.status_code == 200, response.text
    assert response.json()["nuc_normalized"] == "NUC-2026-3002"

    async with session_factory() as session:
        history = (
            await session.scalars(
                select(CaseFileIdentifierHistory).where(
                    CaseFileIdentifierHistory.case_file_id == UUID(case_file["id"])
                )
            )
        ).all()
        assert len(history) == 2
        assert {row.value_normalized for row in history} == {
            "NUC-2026-3001",
            "NUC-2026-3002",
        }

        event = await session.scalar(
            select(AuditEvent).where(
                AuditEvent.entity_id == UUID(case_file["id"]),
                AuditEvent.action == "case_file.identifier_corrected",
            )
        )
        assert event is not None
        assert event.metadata_json is not None
        assert event.metadata_json["previous_value"] == "NUC-2026-3001"
        assert event.metadata_json["new_value"] == "NUC-2026-3002"
        assert event.metadata_json["reason"] == "Correccion de NUC de prueba."


@pytest.mark.asyncio
async def test_box_number_correction_records_history_and_audit(
    seeded_api_client: TestClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    client = seeded_api_client
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    court_id = active_court_id(client)
    box = create_box(client, court_id=court_id)

    response = client.post(
        f"/api/v1/boxes/{box['id']}/number-corrections",
        json={
            "visible_number": "HIST-3001",
            "reason": "Correccion de numero de caja.",
            "expected_version": 1,
        },
        headers=csrf_headers(client),
    )

    assert response.status_code == 200, response.text

    async with session_factory() as session:
        history = (
            await session.scalars(
                select(BoxNumberHistory).where(BoxNumberHistory.box_id == UUID(box["id"]))
            )
        ).all()
        assert len(history) == 1
        assert history[0].new_number == "HIST-3001"

        event = await session.scalar(
            select(AuditEvent).where(
                AuditEvent.entity_id == UUID(box["id"]),
                AuditEvent.action == "box.number_corrected",
            )
        )
        assert event is not None
        assert event.metadata_json is not None
        assert event.metadata_json["reason"] == "Correccion de numero de caja."


@pytest.mark.asyncio
async def test_lifecycle_change_records_before_and_after_audit(
    seeded_api_client: TestClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    client = seeded_api_client
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    court_id = active_court_id(client)
    box = create_box(client, court_id=court_id)

    response = client.post(
        f"/api/v1/boxes/{box['id']}/archive",
        json={"reason": "Archivo auditado.", "expected_version": 1},
        headers=csrf_headers(client),
    )

    assert response.status_code == 200, response.text

    async with session_factory() as session:
        event = await session.scalar(
            select(AuditEvent).where(
                AuditEvent.entity_id == UUID(box["id"]),
                AuditEvent.action == "box.archived",
            )
        )
        assert event is not None
        assert event.before_data is not None
        assert event.after_data is not None
        assert event.before_data["lifecycle_status"] == "ACTIVE"
        assert event.after_data["lifecycle_status"] == "ARCHIVED"
        assert event.metadata_json is not None
        assert event.metadata_json["reason"] == "Archivo auditado."
