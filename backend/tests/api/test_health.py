from __future__ import annotations

from httpx import AsyncClient


async def test_liveness_returns_ok(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/health/live",
        headers={"X-Request-ID": "req-12345678"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"]
    assert body["environment"] == "testing"
    assert response.headers["X-Request-ID"] == "req-12345678"


async def test_request_id_is_generated_when_missing(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health/live")

    assert response.status_code == 200
    assert len(response.headers["X-Request-ID"]) == 32


async def test_unsafe_request_id_is_replaced(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/health/live",
        headers={"X-Request-ID": "<script>alert(1)</script>"},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] != "<script>alert(1)</script>"
    assert len(response.headers["X-Request-ID"]) == 32


async def test_readiness_without_dependencies_returns_503(
    client: AsyncClient,
) -> None:
    response = await client.get("/api/v1/health/ready")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "error"
    assert body["components"]["database"]["status"] == "error"
    assert body["components"]["redis"]["status"] == "error"
