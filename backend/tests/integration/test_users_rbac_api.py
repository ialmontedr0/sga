from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from judicial_archive.core.config import Settings
from judicial_archive.main import create_app
from tests.integration.auth_helpers import (
    ADMIN_PASSWORD,
    ADMIN_USERNAME,
    USER_PASSWORD,
    create_user,
    csrf_headers,
    login,
    logout,
    seed_admin,
)


@pytest_asyncio.fixture
async def api_client(
    migrated_database: str,
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> AsyncIterator[TestClient]:
    await seed_admin(session_factory)
    app = create_app(settings, configure_logs=False)
    with TestClient(app) as client:
        yield client


pytestmark = pytest.mark.integration


def _me(client: TestClient) -> dict[str, object]:
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 200, response.text
    return response.json()  # type: ignore


def test_admin_can_create_and_list_users(api_client: TestClient) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    user_id = create_user(api_client, username="archivista1", role_codes=("ARCHIVISTA",))
    assert user_id

    detail = api_client.get(f"/api/v1/users/{user_id}")
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["username"] == "archivista1"
    assert payload["roles"] == ["ARCHIVISTA"]
    assert "boxes.read" in payload["permissions"]


def test_create_user_with_unknown_role_returns_400(api_client: TestClient) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    response = api_client.post(
        "/api/v1/users/",
        json={
            "username": "rol-invalido",
            "display_name": "Rol Invalido",
            "password": USER_PASSWORD,
            "role_codes": ["NO_EXISTE"],
        },
        headers=csrf_headers(api_client),
    )
    assert response.status_code == 400
    assert "desconocidos" in response.json()["error"]["message"].lower()


def test_lock_and_unlock_user(api_client: TestClient) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    user_id = create_user(api_client, username="bloqueable")

    locked = api_client.post(f"/api/v1/users/{user_id}/lock", headers=csrf_headers(api_client))
    assert locked.status_code == 200

    detail = api_client.get(f"/api/v1/users/{user_id}").json()
    assert detail["status"] == "LOCKED"

    unlocked = api_client.post(f"/api/v1/users/{user_id}/unlock", headers=csrf_headers(api_client))
    assert unlocked.status_code == 200

    detail = api_client.get(f"/api/v1/users/{user_id}").json()
    assert detail["status"] == "ACTIVE"


def test_admin_cannot_lock_self(api_client: TestClient) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    admin_id = _me(api_client)["id"]
    response = api_client.post(f"/api/v1/users/{admin_id}/lock", headers=csrf_headers(api_client))
    assert response.status_code == 400


def test_assign_unknown_role_returns_400(api_client: TestClient) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    user_id = create_user(api_client, username="roles-invalidos")
    response = api_client.post(
        f"/api/v1/users/{user_id}/roles",
        json={"role_codes": ["NO_EXISTE"]},
        headers=csrf_headers(api_client),
    )
    assert response.status_code == 400


def test_update_user_rejects_invalid_status(api_client: TestClient) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    user_id = create_user(api_client, username="estado-invalido")
    response = api_client.patch(
        f"/api/v1/users/{user_id}",
        json={"status": "BOGUS"},
        headers=csrf_headers(api_client),
    )
    assert response.status_code == 422


def test_consulta_role_cannot_list_users(api_client: TestClient) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    create_user(
        api_client,
        username="consulta1",
        password=USER_PASSWORD,
        role_codes=("CONSULTA",),
    )
    logout(api_client)

    login(api_client, "consulta1", USER_PASSWORD)
    response = api_client.get("/api/v1/users/")
    assert response.status_code == 403


def test_reset_password_revokes_sessions(api_client: TestClient) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    admin_id = _me(api_client)["id"]
    new_password = "NewAdminPassword123!"

    response = api_client.post(
        f"/api/v1/users/{admin_id}/reset-password",
        json={"new_password": new_password, "must_change_password": False},
        headers=csrf_headers(api_client),
    )
    assert response.status_code == 200

    assert api_client.get("/api/v1/auth/me").status_code == 401

    login(api_client, ADMIN_USERNAME, new_password)
    assert api_client.get("/api/v1/auth/me").status_code == 200


def test_admin_can_list_and_revoke_sessions(api_client: TestClient) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    admin_id = _me(api_client)["id"]

    sessions = api_client.get(f"/api/v1/users/{admin_id}/sessions")
    assert sessions.status_code == 200
    payload = sessions.json()
    assert payload
    session_id = payload[0]["id"]

    revoked = api_client.post(
        f"/api/v1/users/{admin_id}/sessions/{session_id}/revoke",
        headers=csrf_headers(api_client),
    )
    assert revoked.status_code == 200
    assert api_client.get("/api/v1/auth/me").status_code == 401


def test_change_password_revokes_other_sessions(api_client: TestClient) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    response = api_client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": ADMIN_PASSWORD,
            "new_password": "ChangedPassword123!",
        },
        headers=csrf_headers(api_client),
    )
    assert response.status_code == 200
    # La sesion actual se conserva; las demas se revocan.
    assert api_client.get("/api/v1/auth/me").status_code == 200
