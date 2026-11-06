from __future__ import annotations

from typing import Any, cast

from fastapi.testclient import TestClient

from tests.integration.auth_helpers import csrf_headers


def active_court_id(client: TestClient) -> str:
    response = client.get("/api/v1/courts", params={"status": "ACTIVE", "page_size": 100})
    assert response.status_code == 200, response.text
    items = cast(list[dict[str, Any]], response.json()["items"])
    assert items
    return str(items[0]["id"])


def party_role_id(client: TestClient, code: str = "IMPUTADO") -> str:
    response = client.get("/api/v1/party-roles", params={"page_size": 100})
    assert response.status_code == 200, response.text
    items = cast(list[dict[str, Any]], response.json()["items"])
    for item in items:
        if item["code"] == code:
            return str(item["id"])
    raise AssertionError(f"No se encontro el rol de parte {code}")


def create_box(
    client: TestClient,
    *,
    court_id: str,
    box_type: str = "EXPEDIENTES",
    year: int = 2026,
    visible_number: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, object] = {
        "court_id": court_id,
        "year": year,
        "box_type": box_type,
        "description": "Caja de prueba B7",
    }
    if visible_number is not None:
        payload.update(
            visible_number=visible_number,
            historical_exception=True,
            exception_reason="Numero historico de prueba.",
        )
    response = client.post("/api/v1/boxes", json=payload, headers=csrf_headers(client))
    assert response.status_code == 200, response.text
    return cast(dict[str, Any], response.json())


def create_case_file(
    client: TestClient,
    *,
    court_id: str,
    box_id: str | None,
    nuc: str,
    year: int = 2026,
    **overrides: object,
) -> dict[str, Any]:
    payload: dict[str, object] = {
        "court_id": court_id,
        "box_id": box_id,
        "nuc": nuc,
        "year": year,
    }
    payload.update(overrides)
    response = client.post(
        "/api/v1/case-files",
        json=payload,
        headers=csrf_headers(client),
    )
    assert response.status_code == 200, response.text
    return cast(dict[str, Any], response.json())


def create_administrative_document(
    client: TestClient,
    *,
    box_id: str,
    title: str,
    document_year: int = 2026,
    **overrides: object,
) -> dict[str, Any]:
    payload: dict[str, object] = {
        "box_id": box_id,
        "title": title,
        "document_year": document_year,
    }
    payload.update(overrides)
    response = client.post(
        "/api/v1/administrative-documents",
        json=payload,
        headers=csrf_headers(client),
    )
    assert response.status_code == 200, response.text
    return cast(dict[str, Any], response.json())
