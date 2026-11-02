from __future__ import annotations

from typing import Any, cast
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tests.integration.auth_helpers import (
    ADMIN_PASSWORD,
    ADMIN_USERNAME,
    USER_PASSWORD,
    create_user,
    csrf_headers,
    login,
    logout,
)

pytestmark = pytest.mark.integration


def _sequence_name() -> str:
    return f"b5_{uuid4().hex[:16]}"


def _policy_payload(sequence_name: str, **overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "code": f"B5_{uuid4().hex[:10].upper()}",
        "description": "Politica de prueba B5",
        "scope": "GLOBAL",
        "sequence_name": sequence_name,
        "prefix": "C-",
        "padding": 6,
        "start_value": 4402,
        "step": 1,
    }
    values.update(overrides)
    return values


def _create_policy(
    client: TestClient,
    payload: dict[str, object],
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/numbering-policies",
        json=payload,
        headers=csrf_headers(client),
    )
    assert response.status_code == 201, response.text
    return cast(dict[str, Any], response.json())


async def _sequence_exists(
    session_factory: async_sessionmaker[AsyncSession],
    name: str,
) -> bool:
    async with session_factory() as session:
        value = await session.scalar(
            text("SELECT to_regclass(:name)"),
            {"name": f"public.{name}"},
        )
        return value is not None


async def _nextval(
    session_factory: async_sessionmaker[AsyncSession],
    name: str,
) -> int:
    async with session_factory() as session:
        value = await session.scalar(
            text("SELECT nextval(CAST(:name AS regclass))"),
            {"name": name},
        )
        await session.commit()
        assert value is not None
        return int(value)


async def _drop_sequence(
    session_factory: async_sessionmaker[AsyncSession],
    name: str,
) -> None:
    async with session_factory() as session:
        await session.execute(text(f'DROP SEQUENCE IF EXISTS "{name}"'))
        await session.commit()


@pytest.mark.asyncio
async def test_create_policy_creates_postgresql_sequence(
    api_client: TestClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    name = _sequence_name()
    policy = _create_policy(api_client, _policy_payload(name))

    assert policy["sequence_name"] == name
    assert policy["is_active"] is True
    assert policy["effective_from"] is not None
    assert await _sequence_exists(session_factory, name)


@pytest.mark.asyncio
async def test_sequence_starts_and_advances_with_policy_step(
    api_client: TestClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    name = _sequence_name()
    _create_policy(api_client, _policy_payload(name, start_value=5000, step=7))

    assert await _sequence_exists(session_factory, name)
    assert await _nextval(session_factory, name) == 5000
    assert await _nextval(session_factory, name) == 5007


@pytest.mark.asyncio
async def test_preview_does_not_consume_sequence(
    api_client: TestClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    name = _sequence_name()
    policy = _create_policy(api_client, _policy_payload(name))

    preview = api_client.get(
        f"/api/v1/numbering-policies/{policy['id']}/preview",
        params={"value": 4402},
    )
    assert preview.status_code == 200
    assert preview.json()["formatted"] == "C-004402"

    assert await _nextval(session_factory, name) == 4402


def test_duplicate_sequence_name_is_rejected(api_client: TestClient) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    name = _sequence_name()
    _create_policy(api_client, _policy_payload(name))

    response = api_client.post(
        "/api/v1/numbering-policies",
        json=_policy_payload(name),
        headers=csrf_headers(api_client),
    )
    assert response.status_code == 409


def test_invalid_sequence_name_is_rejected(api_client: TestClient) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    response = api_client.post(
        "/api/v1/numbering-policies",
        json=_policy_payload("nombre-invalido"),
        headers=csrf_headers(api_client),
    )
    assert response.status_code == 422


def test_second_active_global_policy_conflicts(api_client: TestClient) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    _create_policy(api_client, _policy_payload(_sequence_name()))

    response = api_client.post(
        "/api/v1/numbering-policies",
        json=_policy_payload(_sequence_name()),
        headers=csrf_headers(api_client),
    )
    assert response.status_code == 409


def test_scope_columns_must_be_coherent(api_client: TestClient) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    response = api_client.post(
        "/api/v1/numbering-policies",
        json=_policy_payload(_sequence_name(), scope="COURT"),
        headers=csrf_headers(api_client),
    )
    assert response.status_code == 422


def test_deactivate_and_activate_policy(api_client: TestClient) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    policy = _create_policy(api_client, _policy_payload(_sequence_name()))

    deactivated = api_client.post(
        f"/api/v1/numbering-policies/{policy['id']}/deactivate",
        json={"reason": "Prueba"},
        headers=csrf_headers(api_client),
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False

    activated = api_client.post(
        f"/api/v1/numbering-policies/{policy['id']}/activate",
        json={},
        headers=csrf_headers(api_client),
    )
    assert activated.status_code == 200
    assert activated.json()["is_active"] is True


def test_deactivate_policy_requires_reason(api_client: TestClient) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    policy = _create_policy(api_client, _policy_payload(_sequence_name()))

    response = api_client.post(
        f"/api/v1/numbering-policies/{policy['id']}/deactivate",
        json={},
        headers=csrf_headers(api_client),
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_activate_policy_requires_existing_sequence(
    api_client: TestClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    name = _sequence_name()
    policy = _create_policy(api_client, _policy_payload(name))
    await _drop_sequence(session_factory, name)

    deactivated = api_client.post(
        f"/api/v1/numbering-policies/{policy['id']}/deactivate",
        json={"reason": "Prueba"},
        headers=csrf_headers(api_client),
    )
    assert deactivated.status_code == 200

    response = api_client.post(
        f"/api/v1/numbering-policies/{policy['id']}/activate",
        json={},
        headers=csrf_headers(api_client),
    )
    assert response.status_code == 409


def test_update_policy_description_and_notes(api_client: TestClient) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    policy = _create_policy(api_client, _policy_payload(_sequence_name()))

    response = api_client.patch(
        f"/api/v1/numbering-policies/{policy['id']}",
        json={"description": "Descripcion actualizada", "notes": "Nota"},
        headers=csrf_headers(api_client),
    )
    assert response.status_code == 200
    assert response.json()["description"] == "Descripcion actualizada"
    assert response.json()["notes"] == "Nota"


def test_update_policy_rejects_inverted_effective_to(api_client: TestClient) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    policy = _create_policy(
        api_client,
        _policy_payload(_sequence_name(), effective_from="2026-05-01"),
    )

    response = api_client.patch(
        f"/api/v1/numbering-policies/{policy['id']}",
        json={"effective_to": "2026-04-01"},
        headers=csrf_headers(api_client),
    )
    assert response.status_code == 422


def test_numbering_policy_requires_settings_manage(api_client: TestClient) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    create_user(api_client, username="consulta-num", role_codes=("CONSULTA",))
    logout(api_client)
    login(api_client, "consulta-num", USER_PASSWORD)

    response = api_client.post(
        "/api/v1/numbering-policies",
        json=_policy_payload(_sequence_name()),
        headers=csrf_headers(api_client),
    )
    assert response.status_code == 403


def test_list_filter_is_active_returns_only_matching_court_policies(
    api_client: TestClient,
) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    court = api_client.post(
        "/api/v1/courts",
        json={"code_raw": "920", "name": "Tribunal de numeracion"},
        headers=csrf_headers(api_client),
    )
    assert court.status_code == 201
    court_id = court.json()["id"]

    old = _create_policy(
        api_client,
        _policy_payload(_sequence_name(), scope="COURT", court_id=court_id),
    )
    deactivated = api_client.post(
        f"/api/v1/numbering-policies/{old['id']}/deactivate",
        json={"reason": "Prueba"},
        headers=csrf_headers(api_client),
    )
    assert deactivated.status_code == 200

    _create_policy(
        api_client,
        _policy_payload(_sequence_name(), scope="COURT", court_id=court_id),
    )

    response = api_client.get(
        "/api/v1/numbering-policies",
        params={"court_id": court_id, "is_active": "false"},
    )
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["id"] == old["id"]
