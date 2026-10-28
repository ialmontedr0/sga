from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient


@pytest.mark.anyio
@pytest.mark.skipif(os.environ.get("RUN_INTEGRATION") != "1", reason="requiere BD/Redis")
async def test_login_wrong_credentials(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/auth/login", json={"username": "noexiste", "password": "wrongpass123456"}
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "unauthorized"


@pytest.mark.anyio
async def test_me_requires_auth(client: TestClient) -> None:
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401
