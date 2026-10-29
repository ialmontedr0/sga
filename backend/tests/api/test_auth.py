from __future__ import annotations

from fastapi.testclient import TestClient


def test_me_requires_auth(client: TestClient) -> None:
    assert client.get("/api/v1/auth/me").status_code == 401


def test_csrf_endpoint_available_without_auth(client: TestClient) -> None:
    response = client.get("/api/v1/auth/csrf")
    assert response.status_code == 200
    assert response.json()["csrf_token"]
