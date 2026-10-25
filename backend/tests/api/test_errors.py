from __future__ import annotations

from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from judicial_archive.core.errors import NotFoundError
from judicial_archive.main import create_app
from tests.helpers import build_test_settings


@pytest_asyncio.fixture
async def error_client() -> AsyncIterator[AsyncClient]:
    app = create_app(build_test_settings(), configure_logs=False)

    @app.get("/_test/not-found")
    async def _raise_not_found() -> None:
        raise NotFoundError("La caja solicitada no existe.")

    @app.get("/_test/validation")
    async def _validate(value: int) -> dict[str, int]:
        return {"value": value}

    @app.get("/_test/unhandled")
    async def _raise_unhandled() -> None:
        raise RuntimeError("detalle interno que no debe salir")

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://testserver") as http_client:
        yield http_client


async def test_app_error_uses_standard_envelope(error_client: AsyncClient) -> None:
    response = await error_client.get("/_test/not-found")

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "not_found"
    assert body["error"]["message"] == "La caja solicitada no existe."
    assert body["error"]["request_id"]


async def test_validation_error_does_not_echo_input(error_client: AsyncClient) -> None:
    response = await error_client.get("/_test/validation", params={"value": "secreto"})

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert "secreto" not in response.text
    assert body["error"]["details"]["errors"]


async def test_unhandled_error_hides_internal_detail(error_client: AsyncClient) -> None:
    response = await error_client.get("/_test/unhandled")

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "internal_error"
    assert body["error"]["message"] == "Error interno del servidor."
    assert "detalle interno" not in response.text
