from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

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


def _assign(
    client: TestClient,
    box_id,
    position_id,
    *,
    version: int = 1,
    confirmed: bool = True,
):
    return client.post(
        f"/api/v1/locations/boxes/{box_id}/assign",
        json={
            "position_id": str(position_id),
            "confirmed": confirmed,
            "reason": "Prueba de asignacion",
            "expected_version": version,
        },
        headers=csrf_headers(client),
    )


def test_assign_and_get_box_location(seeded_api_client, location_tree) -> None:
    client = seeded_api_client
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)

    response = _assign(client, location_tree.box_ids[0], location_tree.position_ids[0])

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["box"]["box"]["custody_status"] == "IN_PLACE"
    assert payload["box"]["current_position"]["position_id"] == str(location_tree.position_ids[0])
    assert payload["box"]["version"] == 2

    detail = client.get(f"/api/v1/locations/boxes/{location_tree.box_ids[0]}")
    assert detail.status_code == 200, detail.text
    assert detail.json()["version"] == 2
    assert detail.json()["history_count"] == 1


def test_assign_rejects_stale_version(seeded_api_client, location_tree) -> None:
    client = seeded_api_client
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)

    response = _assign(
        client,
        location_tree.box_ids[0],
        location_tree.position_ids[0],
        version=99,
    )

    assert response.status_code == 409
    assert response.json()["error"]["details"]["reason"] == "stale_version"


def test_assign_pending_then_confirm(seeded_api_client, location_tree) -> None:
    client = seeded_api_client
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)

    assigned = _assign(
        client,
        location_tree.box_ids[0],
        location_tree.position_ids[0],
        confirmed=False,
    )
    assert assigned.status_code == 200, assigned.text
    payload = assigned.json()
    assert payload["box"]["box"]["custody_status"] == "PENDING_VERIFICATION"
    assert payload["box"]["box"]["location_state"] == "PENDING_CONFIRMATION"

    confirmed = client.post(
        f"/api/v1/locations/boxes/{location_tree.box_ids[0]}/confirm",
        json={
            "reason": "Confirmacion de ubicacion",
            "expected_version": payload["box"]["version"],
        },
        headers=csrf_headers(client),
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["box"]["box"]["custody_status"] == "IN_PLACE"


def test_unassign_clears_location(seeded_api_client, location_tree) -> None:
    client = seeded_api_client
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)

    assigned = _assign(client, location_tree.box_ids[0], location_tree.position_ids[0])
    assert assigned.status_code == 200, assigned.text

    response = client.post(
        f"/api/v1/locations/boxes/{location_tree.box_ids[0]}/unassign",
        json={
            "reason": "Retiro de ubicacion",
            "expected_version": assigned.json()["box"]["version"],
        },
        headers=csrf_headers(client),
    )

    assert response.status_code == 200, response.text
    assert response.json()["box"]["box"]["custody_status"] == "UNKNOWN"
    assert response.json()["box"]["current_position"] is None


def test_transfer_in_transit_and_complete(seeded_api_client, location_tree) -> None:
    client = seeded_api_client
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    assigned = _assign(
        client,
        location_tree.box_ids[0],
        location_tree.position_ids[0],
    )
    assert assigned.status_code == 200, assigned.text
    version = assigned.json()["box"]["version"]

    response = client.post(
        f"/api/v1/locations/boxes/{location_tree.box_ids[0]}/transfer",
        json={
            "to_position_id": str(location_tree.position_ids[1]),
            "mode": "IN_TRANSIT",
            "confirmed": False,
            "reason": "Traslado en transito",
            "expected_version": version,
        },
        headers=csrf_headers(client),
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["box"]["box"]["custody_status"] == "IN_TRANSIT"
    assert payload["box"]["current_position"] is None
    movement_id = payload["movement"]["id"]
    box_version = payload["box"]["version"]

    completed = client.post(
        f"/api/v1/movements/{movement_id}/complete",
        json={
            "confirmed": True,
            "reason": "Recepcion",
            "expected_version": box_version,
        },
        headers=csrf_headers(client),
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["box"]["box"]["custody_status"] == "IN_PLACE"
    assert completed.json()["box"]["current_position"]["position_id"] == str(
        location_tree.position_ids[1]
    )


def test_scan_by_box_and_position(seeded_api_client, location_tree) -> None:
    client = seeded_api_client
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    _assign(client, location_tree.box_ids[0], location_tree.position_ids[0])

    by_position = client.get(
        "/api/v1/locations/scan",
        params={"position_id": str(location_tree.position_ids[0])},
    )
    assert by_position.status_code == 200, by_position.text
    assert by_position.json()["kind"] == "POSITION"
    assert by_position.json()["position_state"] == "OCCUPIED"

    box_number = by_position.json()["box"]["visible_number"]
    by_box = client.get("/api/v1/locations/scan", params={"box_number": box_number})
    assert by_box.status_code == 200, by_box.text
    assert by_box.json()["kind"] == "BOX"
    assert by_box.json()["location_state"] == "CONFIRMED"


def test_scan_unknown_box_returns_unregistered(seeded_api_client) -> None:
    client = seeded_api_client
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)

    response = client.get("/api/v1/locations/scan", params={"box_number": "NO-EXISTE"})

    assert response.status_code == 200, response.text
    assert response.json()["kind"] == "UNREGISTERED_BOX"
    assert response.json()["operable"] is False


def test_occupancy_and_report(seeded_api_client, location_tree) -> None:
    client = seeded_api_client
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)

    occupancy = client.get(
        "/api/v1/locations/occupancy",
        params={"shelf_id": str(location_tree.shelf_id)},
    )
    assert occupancy.status_code == 200, occupancy.text
    assert occupancy.json()["visible_capacity"] == 3

    report = client.get(
        "/api/v1/locations/reports/occupancy",
        params={"shelf_id": str(location_tree.shelf_id)},
    )
    assert report.status_code == 200, report.text
    assert report.json()["rows"]

    csv_response = client.get(
        "/api/v1/locations/reports/occupancy.csv",
        params={"shelf_id": str(location_tree.shelf_id)},
    )
    assert csv_response.status_code == 200, csv_response.text
    assert "shelf_code" in csv_response.text


def test_assign_requires_manage_permission(seeded_api_client, location_tree) -> None:
    client = seeded_api_client
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    create_user(client, username="consulta_b6", password=USER_PASSWORD)
    logout(client)
    login(client, "consulta_b6", USER_PASSWORD)

    response = _assign(
        client,
        location_tree.box_ids[0],
        location_tree.position_ids[0],
    )

    assert response.status_code == 403
