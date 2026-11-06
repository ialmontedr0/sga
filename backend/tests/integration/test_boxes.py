from __future__ import annotations

from typing import Any, cast
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from tests.integration.auth_helpers import (
    ADMIN_PASSWORD,
    ADMIN_USERNAME,
    csrf_headers,
    login,
)
from tests.integration.b7_helpers import active_court_id, create_box

pytestmark = pytest.mark.integration


def test_create_and_get_box(seeded_api_client: TestClient) -> None:
    client = seeded_api_client
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    court_id = active_court_id(client)

    box = create_box(client, court_id=court_id, box_type="EXPEDIENTES")

    assert box["visible_number"]
    assert box["lifecycle_status"] == "ACTIVE"
    assert box["custody_status"] == "UNKNOWN"
    assert box["version"] == 1

    detail = client.get(f"/api/v1/boxes/{box['id']}")
    assert detail.status_code == 200, detail.text
    assert detail.json()["id"] == box["id"]


def test_list_boxes_filters_by_court_type_and_year(seeded_api_client: TestClient) -> None:
    client = seeded_api_client
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    court_id = active_court_id(client)

    create_box(client, court_id=court_id, box_type="EXPEDIENTES", year=2025)
    create_box(client, court_id=court_id, box_type="DOCUMENTOS_ADMINISTRATIVOS", year=2026)

    response = client.get(
        "/api/v1/boxes",
        params={"court_id": court_id, "box_type": "EXPEDIENTES", "year": 2025},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["box_type"] == "EXPEDIENTES"
    assert payload["items"][0]["year"] == 2025


def test_manual_box_number_requires_exception_reason(seeded_api_client: TestClient) -> None:
    client = seeded_api_client
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    court_id = active_court_id(client)

    missing_exception = client.post(
        "/api/v1/boxes",
        json={
            "court_id": court_id,
            "year": 2026,
            "box_type": "EXPEDIENTES",
            "visible_number": "HIST-0001",
        },
        headers=csrf_headers(client),
    )
    assert missing_exception.status_code == 422

    missing_reason = client.post(
        "/api/v1/boxes",
        json={
            "court_id": court_id,
            "year": 2026,
            "box_type": "EXPEDIENTES",
            "visible_number": "HIST-0001",
            "historical_exception": True,
        },
        headers=csrf_headers(client),
    )
    assert missing_reason.status_code == 422

    created = create_box(
        client,
        court_id=court_id,
        visible_number="HIST-0001",
    )
    assert created["visible_number"] == "HIST-0001"


def test_duplicate_manual_box_number_is_rejected(seeded_api_client: TestClient) -> None:
    client = seeded_api_client
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    court_id = active_court_id(client)

    create_box(client, court_id=court_id, visible_number="HIST-0002")
    response = client.post(
        "/api/v1/boxes",
        json={
            "court_id": court_id,
            "year": 2026,
            "box_type": "EXPEDIENTES",
            "visible_number": "HIST-0002",
            "historical_exception": True,
            "exception_reason": "Duplicado de prueba.",
        },
        headers=csrf_headers(client),
    )

    assert response.status_code == 409
    assert response.json()["error"]["details"]["reason"] == "duplicate_visible_number"


def test_update_box_and_reject_stale_version(seeded_api_client: TestClient) -> None:
    client = seeded_api_client
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    court_id = active_court_id(client)
    box = create_box(client, court_id=court_id)

    updated = client.patch(
        f"/api/v1/boxes/{box['id']}",
        json={"description": "Descripcion actualizada", "expected_version": 1},
        headers=csrf_headers(client),
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["description"] == "Descripcion actualizada"
    assert updated.json()["version"] == 2

    stale = client.patch(
        f"/api/v1/boxes/{box['id']}",
        json={"description": "Otra descripcion", "expected_version": 1},
        headers=csrf_headers(client),
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["details"]["reason"] == "stale_version"


def test_correct_box_number_records_history(seeded_api_client: TestClient) -> None:
    client = seeded_api_client
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    court_id = active_court_id(client)
    box = create_box(client, court_id=court_id)
    original_number = box["visible_number"]

    corrected = client.post(
        f"/api/v1/boxes/{box['id']}/number-corrections",
        json={
            "visible_number": "HIST-0100",
            "reason": "Correccion de numero historico.",
            "expected_version": 1,
        },
        headers=csrf_headers(client),
    )

    assert corrected.status_code == 200, corrected.text
    assert corrected.json()["visible_number"] == "HIST-0100"

    history = client.get(f"/api/v1/boxes/{box['id']}/number-history")
    assert history.status_code == 200, history.text
    payload = history.json()
    assert payload["total"] == 1
    assert payload["items"][0]["previous_number"] == original_number
    assert payload["items"][0]["new_number"] == "HIST-0100"


def test_archive_and_void_boxes(seeded_api_client: TestClient) -> None:
    client = seeded_api_client
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    court_id = active_court_id(client)
    archived = create_box(client, court_id=court_id)
    voided = create_box(client, court_id=court_id)

    archive_response = client.post(
        f"/api/v1/boxes/{archived['id']}/archive",
        json={"reason": "Archivo de prueba.", "expected_version": 1},
        headers=csrf_headers(client),
    )
    assert archive_response.status_code == 200, archive_response.text
    assert archive_response.json()["lifecycle_status"] == "ARCHIVED"

    void_response = client.post(
        f"/api/v1/boxes/{voided['id']}/void",
        json={"reason": "Anulacion de prueba.", "expected_version": 1},
        headers=csrf_headers(client),
    )
    assert void_response.status_code == 200, void_response.text
    assert void_response.json()["lifecycle_status"] == "VOIDED"

    repeated = client.post(
        f"/api/v1/boxes/{archived['id']}/archive",
        json={"reason": "Repetido.", "expected_version": 2},
        headers=csrf_headers(client),
    )
    assert repeated.status_code == 409
    assert repeated.json()["error"]["details"]["reason"] == "box_not_active"


def test_box_content_summary_starts_empty(seeded_api_client: TestClient) -> None:
    client = seeded_api_client
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    court_id = active_court_id(client)
    box = create_box(client, court_id=court_id)

    response = client.get(f"/api/v1/boxes/{box['id']}/content-summary")

    assert response.status_code == 200, response.text
    payload = cast(dict[str, Any], response.json())
    assert payload["case_file_count"] == 0
    assert payload["administrative_document_count"] == 0
    assert payload["total_count"] == 0


def test_get_missing_box_returns_not_found(seeded_api_client: TestClient) -> None:
    client = seeded_api_client
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)

    response = client.get(f"/api/v1/boxes/{uuid4()}")

    assert response.status_code == 404
