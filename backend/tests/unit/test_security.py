from __future__ import annotations

import pytest

from judicial_archive.core.security import (
    generate_opaque_token,
    hash_opaque_token,
    hash_password,
    verify_opaque_token,
    verify_password,
)


def test_password_hash_and_verify() -> None:
    password = "Contrasena-Segura-2026"
    password_hash = hash_password(password)

    assert password_hash != password
    assert password not in password_hash
    assert verify_password(password, password_hash) is True
    assert verify_password("otra-contrasena", password_hash) is False


def test_empty_password_is_rejected() -> None:
    with pytest.raises(ValueError, match="no puede estar vacia"):
        hash_password("")


def test_verify_password_with_invalid_hash_returns_false() -> None:
    assert verify_password("cualquiera", "hash-invalido") is False


def test_opaque_token_generation_and_hash() -> None:
    token = generate_opaque_token()
    other = generate_opaque_token()

    assert token != other
    assert len(token) >= 43
    assert hash_opaque_token(token) == hash_opaque_token(token)
    assert hash_opaque_token(token) != hash_opaque_token(other)
    assert verify_opaque_token(token, hash_opaque_token(token)) is True
    assert verify_opaque_token(other, hash_opaque_token(token)) is False


def test_token_requires_minimum_entropy() -> None:
    with pytest.raises(ValueError, match="al menos 32 bytes"):
        generate_opaque_token(16)
