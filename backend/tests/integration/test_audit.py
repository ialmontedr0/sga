from __future__ import annotations

from typing import cast
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from judicial_archive.modules.audit.models import AuditEvent
from tests.integration.auth_helpers import (
    ADMIN_PASSWORD,
    ADMIN_USERNAME,
    csrf_headers,
    login,
)

pytestmark = pytest.mark.integration


async def _events(session: AsyncSession, entity_id: UUID) -> list[AuditEvent]:
    rows = await session.scalars(
        select(AuditEvent)
        .where(AuditEvent.entity_id == entity_id)
        .order_by(AuditEvent.occurred_at, AuditEvent.id)
    )
    return list(rows.all())


def _create_area(client: TestClient, code: str = "ZA") -> dict[str, object]:
    response = client.post(
        "/api/v1/areas",
        json={"code": code, "name": f"Zona {code}"},
        headers=csrf_headers(client),
    )
    assert response.status_code == 201, response.text
    return cast(dict[str, object], response.json())


@pytest.mark.asyncio
async def test_area_create_writes_audit_event(
    api_client: TestClient,
    db_session: AsyncSession,
) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    area = _create_area(api_client, "ZA")

    events = await _events(db_session, UUID(str(area["id"])))
    created = [event for event in events if event.action == "area.created"]
    assert len(created) == 1

    event = created[0]
    assert event.actor_type == "USER"
    assert event.actor_user_id is not None
    assert event.actor_label == ADMIN_USERNAME
    assert event.before_data is None
    assert event.after_data is not None
    assert event.after_data["code"] == "ZA"
    assert event.after_data["status"] == "ACTIVE"
    assert event.source == "API"
    assert event.result == "SUCCESS"
    assert event.request_id


@pytest.mark.asyncio
async def test_area_update_and_deactivation_record_before_after(
    api_client: TestClient,
    db_session: AsyncSession,
) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    area = _create_area(api_client, "ZB")
    area_id = area["id"]

    updated = api_client.patch(
        f"/api/v1/areas/{area_id}",
        json={"name": "Zona actualizada"},
        headers=csrf_headers(api_client),
    )
    assert updated.status_code == 200

    deactivated = api_client.post(
        f"/api/v1/areas/{area_id}/deactivate",
        json={"reason": "Motivo de auditoria"},
        headers=csrf_headers(api_client),
    )
    assert deactivated.status_code == 200

    events = await _events(db_session, UUID(str(area_id)))
    by_action = {event.action: event for event in events}

    update_event = by_action["area.updated"]
    assert update_event.before_data is not None
    assert update_event.before_data["name"] == "Zona ZB"
    assert update_event.after_data is not None
    assert update_event.after_data["name"] == "Zona actualizada"

    deactivate_event = by_action["area.deactivated"]
    assert deactivate_event.after_data is not None
    assert deactivate_event.after_data["status"] == "INACTIVE"
    assert deactivate_event.metadata_json == {"reason": "Motivo de auditoria"}


@pytest.mark.asyncio
async def test_failed_area_create_does_not_write_audit(
    api_client: TestClient,
    db_session: AsyncSession,
) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    _create_area(api_client, "ZC")

    response = api_client.post(
        "/api/v1/areas",
        json={"code": "ZC", "name": "Zona duplicada"},
        headers=csrf_headers(api_client),
    )
    assert response.status_code == 409

    count = await db_session.scalar(
        select(func.count())
        .select_from(AuditEvent)
        .where(
            AuditEvent.action == "area.created",
            AuditEvent.after_data["code"].astext == "ZC",
        )
    )
    assert count == 1


@pytest.mark.asyncio
async def test_duplicate_court_codes_create_two_audit_events(
    api_client: TestClient,
    db_session: AsyncSession,
) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    payload = {"code_raw": "589", "name": "Juzgado de Instruccion"}
    first = api_client.post(
        "/api/v1/courts",
        json=payload,
        headers=csrf_headers(api_client),
    )
    second = api_client.post(
        "/api/v1/courts",
        json={"code_raw": "589", "name": "Juzgado en Atencion Permanente"},
        headers=csrf_headers(api_client),
    )
    assert first.status_code == 201
    assert second.status_code == 201

    for court in (first.json(), second.json()):
        events = await _events(db_session, UUID(str(court["id"])))
        assert [event.action for event in events] == ["court.created"]
        assert events[0].after_data is not None
        assert events[0].after_data["code_normalized"] == "589"


@pytest.mark.asyncio
async def test_numbering_policy_create_writes_audit_event(
    api_client: TestClient,
    db_session: AsyncSession,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    sequence_name = f"b5_audit_{uuid4().hex[:12]}"
    try:
        response = api_client.post(
            "/api/v1/numbering-policies",
            json={
                "code": f"AUDIT_{uuid4().hex[:8].upper()}",
                "scope": "GLOBAL",
                "sequence_name": sequence_name,
                "start_value": 7000,
                "step": 1,
                "padding": 0,
            },
            headers=csrf_headers(api_client),
        )
        assert response.status_code == 201, response.text
        policy = response.json()

        events = await _events(db_session, UUID(str(policy["id"])))
        assert [event.action for event in events] == ["numbering_policy.created"]
        assert events[0].after_data is not None
        assert events[0].after_data["sequence_name"] == sequence_name
        assert events[0].after_data["scope"] == "GLOBAL"
    finally:
        async with session_factory() as session:
            await session.execute(text(f'DROP SEQUENCE IF EXISTS "{sequence_name}"'))
            await session.commit()
