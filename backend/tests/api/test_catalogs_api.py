from __future__ import annotations

from typing import Any, cast

from fastapi.testclient import TestClient

BASE_PATHS = {
    "/api/v1/courts",
    "/api/v1/identifier-profiles",
    "/api/v1/areas",
    "/api/v1/box-types",
    "/api/v1/shelves",
    "/api/v1/trays",
    "/api/v1/positions",
    "/api/v1/numbering-policies",
    "/api/v1/party-roles",
    "/api/v1/resolution-types",
    "/api/v1/settings",
}

REQUIRED_PATH_SUFFIXES = {
    "/capacity/preview",
    "/capacity/apply",
    "/retire",
    "/activate",
    "/deactivate",
}


def _openapi(client: TestClient) -> dict[str, Any]:
    response = client.get("/openapi.json")
    assert response.status_code == 200, response.text
    return cast(dict[str, Any], response.json())


def test_b5_openapi_contains_required_catalog_paths(client: TestClient) -> None:
    paths = _openapi(client)["paths"]
    assert isinstance(paths, dict)

    missing = BASE_PATHS - set(paths)
    assert not missing, f"Faltan rutas B5: {sorted(missing)}"

    for suffix in REQUIRED_PATH_SUFFIXES:
        assert any(path.endswith(suffix) for path in paths), f"Falta una ruta {suffix}"


def test_catalog_resources_do_not_expose_delete(client: TestClient) -> None:
    paths = _openapi(client)["paths"]
    assert isinstance(paths, dict)

    for path, operations in paths.items():
        if not path.startswith("/api/v1/"):
            continue
        if not any(path == base or path.startswith(f"{base}/") for base in BASE_PATHS):
            continue
        assert isinstance(operations, dict)
        assert "delete" not in operations, f"{path} no debe permitir DELETE"


def test_box_types_is_read_only(client: TestClient) -> None:
    paths = _openapi(client)["paths"]
    operations = paths["/api/v1/box-types"]
    assert set(operations) == {"get"}


def test_identifier_profile_update_schema_excludes_pattern(client: TestClient) -> None:
    schema = _openapi(client)["components"]["schemas"]["IdentifierProfileUpdate"]
    assert set(schema["properties"]) == {"notes", "effective_to"}


def test_capacity_apply_requires_expected_version(client: TestClient) -> None:
    schema = _openapi(client)["components"]["schemas"]["CapacityApplyRequest"]
    assert {"levels", "positions_per_level", "expected_version"} <= set(schema["required"])


def test_catalog_reads_require_authentication(client: TestClient) -> None:
    for path in (
        "/api/v1/courts",
        "/api/v1/areas",
        "/api/v1/box-types",
        "/api/v1/identifier-profiles",
        "/api/v1/numbering-policies",
        "/api/v1/party-roles",
        "/api/v1/resolution-types",
        "/api/v1/settings",
    ):
        response = client.get(path)
        assert response.status_code == 401, path


def test_catalog_mutations_require_csrf(client: TestClient) -> None:
    response = client.post(
        "/api/v1/courts",
        json={"code_raw": "999", "name": "Tribunal sin CSRF"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["details"] == {"reason": "csrf"}
