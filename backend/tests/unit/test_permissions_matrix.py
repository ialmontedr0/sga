from __future__ import annotations

from judicial_archive.db.seed_rbac import PERMISSIONS, ROLE_NAMES, ROLE_PERMISSIONS


def test_permission_codes_are_unique() -> None:
    codes = [code for code, _, _ in PERMISSIONS]
    assert len(codes) == len(set(codes))


def test_every_roles_has_a_permission_mapping() -> None:
    assert set(ROLE_PERMISSIONS) == set(ROLE_NAMES)


def test_role_permissions_only_preference_known_permissions() -> None:
    known = {code for code, _, _ in PERMISSIONS}
    for role_code, codes in ROLE_PERMISSIONS.items():
        unknown = set(codes) - known
        assert not unknown, f"{role_code} referencia permisos inexistentes: {unknown}"


def test_administrador_has_every_permission() -> None:
    admin = set(ROLE_PERMISSIONS["ADMINISTRADOR"])
    assert admin == {code for code, _, _ in PERMISSIONS}


def test_permission_format_matches_database_check() -> None:
    import re

    pattern = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")
    for code, _, _ in PERMISSIONS:
        assert pattern.fullmatch(code), code
