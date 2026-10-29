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


def test_login_without_csrf_is_rejected(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/v1/auth/login",
        json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
    )
    assert response.status_code == 403
    assert response.json()["error"]["details"] == {"reason": "csrf"}


def test_login_with_csrf_succeeds(api_client: TestClient) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    response = api_client.get("/api/v1/auth/me")
    assert response.status_code == 200
    assert response.json()["username"] == ADMIN_USERNAME


def test_mutation_without_header_is_rejected_after_login(
    api_client: TestClient,
) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    response = api_client.post(
        "/api/v1/users/",
        json={
            "username": "sin-csrf",
            "display_name": "Sin CSRF",
            "password": "UserPassword123!",
            "role_codes": ["CONSULTA"],
        },
    )
    assert response.status_code == 403
    assert response.json()["error"]["details"] == {"reason": "csrf"}


def test_safe_get_after_login_does_not_require_header(api_client: TestClient) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    assert api_client.get("/api/v1/users/").status_code == 200


def test_csrf_endpoint_returns_same_token_as_cookie(api_client: TestClient) -> None:
    token = get_csrf(api_client)
    assert api_client.cookies.get("sga_csrf") == token
