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
    csrf_headers,
    get_csrf,
    login,
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


def test_full_auth_flow(api_client: TestClient) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)

    me = api_client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["username"] == ADMIN_USERNAME
    assert "users.read" in me.json()["permissions"]

    logout = api_client.post("/api/v1/auth/logout", headers=csrf_headers(api_client))
    assert logout.status_code == 200
    assert api_client.get("/api/v1/auth/me").status_code == 401


def test_login_wrong_credentials(api_client: TestClient) -> None:
    token = get_csrf(api_client)
    response = api_client.post(
        "/api/v1/auth/login",
        json={"username": "noexiste", "password": "wrongpass123456"},
        headers={"X-CSRF-Token": token},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"
