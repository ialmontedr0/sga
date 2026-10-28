from __future__ import annotations

from judicial_archive.core import security


def test_hash_and_verify_password() -> None:
    pwd = "SuperSegura123!"
    h = security.hash_password(pwd)
    assert security.verify_password(pwd, h) is True
    assert security.verify_password("otra", h) is False


def test_generate_tokens() -> None:
    t = security.generate_session_token()
    assert len(t) > 20
    h = security.hash_opaque_token(t)
    assert security.verify_opaque_token(t, h) is True
    assert security.verify_opaque_token("x", h) is False


def test_csrf_token() -> None:
    c = security.generate_csrf_token()
    assert len(c) > 10
