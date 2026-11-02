from __future__ import annotations

from typing import Any, cast

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


def _create_court(
    client: TestClient,
    *,
    code: str = "901",
    name: str = "Tribunal de prueba",
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/courts",
        json={"code_raw": code, "name": name},
        headers=csrf_headers(client),
    )
    assert response.status_code == 201, response.text
    return cast(dict[str, Any], response.json())


def _create_area(client: TestClient, *, code: str = "ZZ") -> dict[str, Any]:
    response = client.post(
        "/api/v1/areas",
        json={"code": code, "name": f"Zona {code}"},
        headers=csrf_headers(client),
    )
    assert response.status_code == 201, response.text
    return cast(dict[str, Any], response.json())


def _profile_payload(court_id: str, **overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "court_id": court_id,
        "identifier_kind": "NUC",
        "pattern": r"^\d{5}$",
        "examples": ["00001", "00002", "00003"],
        "rejects": ["ABCDE"],
        "strict": True,
        "effective_from": "2026-01-01",
    }
    values.update(overrides)
    return values


def test_consulta_cannot_create_court(api_client: TestClient) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    create_user(api_client, username="consulta-b5", role_codes=("CONSULTA",))
    logout(api_client)
    login(api_client, "consulta-b5", USER_PASSWORD)

    response = api_client.post(
        "/api/v1/courts",
        json={"code_raw": "999", "name": "Tribunal de prueba"},
        headers=csrf_headers(api_client),
    )
    assert response.status_code == 403


def test_supervisor_can_manage_catalog_but_not_settings(api_client: TestClient) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    create_user(api_client, username="supervisor-b5", role_codes=("SUPERVISOR",))
    logout(api_client)
    login(api_client, "supervisor-b5", USER_PASSWORD)

    created = api_client.post(
        "/api/v1/courts",
        json={"code_raw": "998", "name": "Tribunal de supervisor"},
        headers=csrf_headers(api_client),
    )
    assert created.status_code == 201

    forbidden = api_client.put(
        "/api/v1/settings/system.timezone",
        json={"value": "UTC", "value_type": "STRING", "description": "Zona horaria"},
        headers=csrf_headers(api_client),
    )
    assert forbidden.status_code == 403


def test_consulta_can_read_catalogs_but_not_settings(api_client: TestClient) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    create_user(api_client, username="consulta-lectura", role_codes=("CONSULTA",))
    logout(api_client)
    login(api_client, "consulta-lectura", USER_PASSWORD)

    assert api_client.get("/api/v1/courts").status_code == 200
    assert api_client.get("/api/v1/settings").status_code == 403


def test_duplicate_court_codes_are_allowed(api_client: TestClient) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    payload = {"code_raw": "589", "name": "Juzgado de Instruccion"}
    first = api_client.post("/api/v1/courts", json=payload, headers=csrf_headers(api_client))
    second = api_client.post(
        "/api/v1/courts",
        json={"code_raw": "589", "name": "Juzgado en Atencion Permanente"},
        headers=csrf_headers(api_client),
    )
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["code_normalized"] == "589"
    assert second.json()["code_normalized"] == "589"


def test_court_has_no_delete_endpoint(api_client: TestClient) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    court = _create_court(api_client, code="997", name="Tribunal sin borrado")
    response = api_client.delete(
        f"/api/v1/courts/{court['id']}",
        headers=csrf_headers(api_client),
    )
    assert response.status_code == 405


def test_court_crud_and_status_flow(api_client: TestClient) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    court = _create_court(api_client, code=" 995 ", name=" Tribunal original ")
    court_id = court["id"]
    assert court["code_raw"] == "995"
    assert court["code_normalized"] == "995"

    detail = api_client.get(f"/api/v1/courts/{court_id}")
    assert detail.status_code == 200
    assert detail.json()["name"] == "Tribunal original"

    listing = api_client.get("/api/v1/courts", params={"q": "995"})
    assert listing.status_code == 200
    assert any(item["id"] == court_id for item in listing.json()["items"])

    updated = api_client.patch(
        f"/api/v1/courts/{court_id}",
        json={
            "name": "Tribunal actualizado",
            "effective_from": None,
            "effective_to": None,
        },
        headers=csrf_headers(api_client),
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["name"] == "Tribunal actualizado"

    deactivated = api_client.post(
        f"/api/v1/courts/{court_id}/deactivate",
        json={"reason": "Prueba de desactivacion"},
        headers=csrf_headers(api_client),
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["status"] == "INACTIVE"

    activated = api_client.post(
        f"/api/v1/courts/{court_id}/activate",
        json={},
        headers=csrf_headers(api_client),
    )
    assert activated.status_code == 200
    assert activated.json()["status"] == "ACTIVE"


def test_deactivate_court_requires_reason(api_client: TestClient) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    court = _create_court(api_client, code="994")
    response = api_client.post(
        f"/api/v1/courts/{court['id']}/deactivate",
        json={},
        headers=csrf_headers(api_client),
    )
    assert response.status_code == 422


def test_area_code_is_unique_via_api(api_client: TestClient) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    payload = {"code": "z", "name": "Zona Z"}
    first = api_client.post("/api/v1/areas", json=payload, headers=csrf_headers(api_client))
    second = api_client.post("/api/v1/areas", json=payload, headers=csrf_headers(api_client))
    assert first.status_code == 201
    assert first.json()["code"] == "Z"
    assert second.status_code == 409


def test_area_crud_and_status_flow(api_client: TestClient) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    area = _create_area(api_client, code="ZZ")
    area_id = area["id"]

    detail = api_client.get(f"/api/v1/areas/{area_id}")
    assert detail.status_code == 200

    listing = api_client.get("/api/v1/areas", params={"q": "ZZ"})
    assert listing.status_code == 200
    assert any(item["id"] == area_id for item in listing.json()["items"])

    updated = api_client.patch(
        f"/api/v1/areas/{area_id}",
        json={"name": "Zona actualizada"},
        headers=csrf_headers(api_client),
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Zona actualizada"

    deactivated = api_client.post(
        f"/api/v1/areas/{area_id}/deactivate",
        json={"reason": "Prueba"},
        headers=csrf_headers(api_client),
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["status"] == "INACTIVE"

    activated = api_client.post(
        f"/api/v1/areas/{area_id}/activate",
        json={},
        headers=csrf_headers(api_client),
    )
    assert activated.status_code == 200
    assert activated.json()["status"] == "ACTIVE"


def test_area_deactivation_requires_reason(api_client: TestClient) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    area = _create_area(api_client, code="ZX")
    response = api_client.post(
        f"/api/v1/areas/{area['id']}/deactivate",
        json={},
        headers=csrf_headers(api_client),
    )
    assert response.status_code == 422


def test_strict_profile_requires_three_examples(api_client: TestClient) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    court = _create_court(api_client, code="910")

    invalid = api_client.post(
        "/api/v1/identifier-profiles",
        json=_profile_payload(court["id"], examples=["00001", "00002"]),
        headers=csrf_headers(api_client),
    )
    assert invalid.status_code == 422

    valid = api_client.post(
        "/api/v1/identifier-profiles",
        json=_profile_payload(court["id"]),
        headers=csrf_headers(api_client),
    )
    assert valid.status_code == 201, valid.text
    assert valid.json()["strict"] is True
    assert valid.json()["is_active"] is True


def test_profile_rejects_invalid_pattern(api_client: TestClient) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    court = _create_court(api_client, code="911")
    response = api_client.post(
        "/api/v1/identifier-profiles",
        json=_profile_payload(court["id"], pattern=r"["),
        headers=csrf_headers(api_client),
    )
    assert response.status_code == 422


def test_second_active_profile_conflicts(api_client: TestClient) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    court = _create_court(api_client, code="912")
    first = api_client.post(
        "/api/v1/identifier-profiles",
        json=_profile_payload(court["id"]),
        headers=csrf_headers(api_client),
    )
    assert first.status_code == 201

    second = api_client.post(
        "/api/v1/identifier-profiles",
        json=_profile_payload(court["id"], effective_from="2026-02-01"),
        headers=csrf_headers(api_client),
    )
    assert second.status_code == 409


def test_replace_profile_closes_previous_profile(api_client: TestClient) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    court = _create_court(api_client, code="913")
    old = api_client.post(
        "/api/v1/identifier-profiles",
        json=_profile_payload(court["id"]),
        headers=csrf_headers(api_client),
    )
    assert old.status_code == 201
    old_id = old.json()["id"]

    replaced = api_client.post(
        f"/api/v1/identifier-profiles/{old_id}/replace",
        json={
            "pattern": r"^\d{6}$",
            "examples": ["000001", "000002", "000003"],
            "rejects": ["ABCDEF"],
            "strict": True,
            "effective_from": "2026-02-01",
        },
        headers=csrf_headers(api_client),
    )
    assert replaced.status_code == 200, replaced.text
    new_id = replaced.json()["id"]
    assert new_id != old_id
    assert replaced.json()["is_active"] is True
    assert replaced.json()["effective_from"] == "2026-02-01"

    old_detail = api_client.get(f"/api/v1/identifier-profiles/{old_id}")
    assert old_detail.status_code == 200
    assert old_detail.json()["is_active"] is False
    assert old_detail.json()["effective_to"] == "2026-01-31"

    listing = api_client.get(
        "/api/v1/identifier-profiles",
        params={"court_id": court["id"], "identifier_kind": "NUC"},
    )
    assert listing.status_code == 200
    assert listing.json()["total"] == 2


def test_replace_profile_requires_later_effective_from(api_client: TestClient) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    court = _create_court(api_client, code="914")
    old = api_client.post(
        "/api/v1/identifier-profiles",
        json=_profile_payload(court["id"], effective_from="2026-03-01"),
        headers=csrf_headers(api_client),
    )
    assert old.status_code == 201

    response = api_client.post(
        f"/api/v1/identifier-profiles/{old.json()['id']}/replace",
        json={
            "pattern": r"^\d{6}$",
            "examples": ["000001", "000002", "000003"],
            "strict": True,
            "effective_from": "2026-03-01",
        },
        headers=csrf_headers(api_client),
    )
    assert response.status_code == 422


def test_profile_deactivate_and_reactivate(api_client: TestClient) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    court = _create_court(api_client, code="915")
    created = api_client.post(
        "/api/v1/identifier-profiles",
        json=_profile_payload(court["id"]),
        headers=csrf_headers(api_client),
    )
    assert created.status_code == 201
    profile_id = created.json()["id"]

    deactivated = api_client.post(
        f"/api/v1/identifier-profiles/{profile_id}/deactivate",
        json={"reason": "Prueba"},
        headers=csrf_headers(api_client),
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False

    activated = api_client.post(
        f"/api/v1/identifier-profiles/{profile_id}/activate",
        json={},
        headers=csrf_headers(api_client),
    )
    assert activated.status_code == 200
    assert activated.json()["is_active"] is True


def test_profile_patch_only_updates_notes_and_effective_to(api_client: TestClient) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    court = _create_court(api_client, code="916")
    created = api_client.post(
        "/api/v1/identifier-profiles",
        json=_profile_payload(court["id"]),
        headers=csrf_headers(api_client),
    )
    assert created.status_code == 201
    profile_id = created.json()["id"]

    updated = api_client.patch(
        f"/api/v1/identifier-profiles/{profile_id}",
        json={"notes": "Nota actualizada", "effective_to": "2026-12-31"},
        headers=csrf_headers(api_client),
    )
    assert updated.status_code == 200
    assert updated.json()["notes"] == "Nota actualizada"
    assert updated.json()["effective_to"] == "2026-12-31"
    assert updated.json()["pattern"] == r"^\d{5}$"


def test_profile_requires_active_court(api_client: TestClient) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    court = _create_court(api_client, code="917")
    deactivated = api_client.post(
        f"/api/v1/courts/{court['id']}/deactivate",
        json={"reason": "Prueba"},
        headers=csrf_headers(api_client),
    )
    assert deactivated.status_code == 200

    response = api_client.post(
        "/api/v1/identifier-profiles",
        json=_profile_payload(court["id"]),
        headers=csrf_headers(api_client),
    )
    assert response.status_code == 422


def test_get_seeded_timezone(seeded_api_client: TestClient) -> None:
    login(seeded_api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    response = seeded_api_client.get("/api/v1/settings/system.timezone")
    assert response.status_code == 200
    assert response.json()["value"] == "America/Santo_Domingo"
    assert response.json()["value_type"] == "STRING"


def test_admin_can_update_timezone(seeded_api_client: TestClient) -> None:
    login(seeded_api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    me = seeded_api_client.get("/api/v1/auth/me")
    assert me.status_code == 200

    response = seeded_api_client.put(
        "/api/v1/settings/system.timezone",
        json={"value": "UTC", "value_type": "STRING", "description": "Zona horaria"},
        headers=csrf_headers(seeded_api_client),
    )
    assert response.status_code == 200, response.text
    assert response.json()["value"] == "UTC"
    assert response.json()["updated_by"] == me.json()["id"]

    detail = seeded_api_client.get("/api/v1/settings/system.timezone")
    assert detail.status_code == 200
    assert detail.json()["value"] == "UTC"


def test_invalid_timezone_is_rejected(seeded_api_client: TestClient) -> None:
    login(seeded_api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    response = seeded_api_client.put(
        "/api/v1/settings/system.timezone",
        json={"value": "No/Existe", "value_type": "STRING", "description": "Zona horaria"},
        headers=csrf_headers(seeded_api_client),
    )
    assert response.status_code == 422


def test_sensitive_setting_key_is_rejected(seeded_api_client: TestClient) -> None:
    login(seeded_api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    response = seeded_api_client.put(
        "/api/v1/settings/db.password",
        json={"value": "secreto", "value_type": "STRING", "description": "No permitido"},
        headers=csrf_headers(seeded_api_client),
    )
    assert response.status_code == 422


def test_setting_type_change_is_rejected(seeded_api_client: TestClient) -> None:
    login(seeded_api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    key = "b5.type-change"
    created = seeded_api_client.put(
        f"/api/v1/settings/{key}",
        json={"value": "texto", "value_type": "STRING", "description": "Prueba de tipo"},
        headers=csrf_headers(seeded_api_client),
    )
    assert created.status_code == 200, created.text

    response = seeded_api_client.put(
        f"/api/v1/settings/{key}",
        json={"value": 5, "value_type": "INTEGER", "description": "Tipo cambiado"},
        headers=csrf_headers(seeded_api_client),
    )
    assert response.status_code == 409


def test_settings_list_contains_seeded_timezone(seeded_api_client: TestClient) -> None:
    login(seeded_api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    response = seeded_api_client.get("/api/v1/settings")
    assert response.status_code == 200
    keys = {item["key"] for item in response.json()["items"]}
    assert "system.timezone" in keys
