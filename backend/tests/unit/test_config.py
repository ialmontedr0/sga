from __future__ import annotations

import pytest
from pydantic import ValidationError

from judicial_archive.core.config import Environment, Settings
from tests.helpers import build_test_settings


def test_valid_settings() -> None:
    settings = build_test_settings()
    assert settings.environment is Environment.TESTING
    assert settings.api_v1_prefix == "/api/v1"
    assert settings.cors_origins == ["http://localhost:5173"]


def test_short_secret_key_is_rejected() -> None:
    with pytest.raises(ValidationError):
        build_test_settings(secret_key="corto")


def test_api_prefix_must_start_with_slash() -> None:
    with pytest.raises(ValidationError):
        build_test_settings(api_v1_prefix="api/v1")


def test_api_prefix_must_not_end_with_slash() -> None:
    with pytest.raises(ValidationError):
        build_test_settings(api_v1_prefix="/api/v1/")


def test_production_accepts_secure_configuration() -> None:
    settings = build_test_settings(
        environment=Environment.PRODUCTION,
        debug=False,
        docs_enabled=False,
        log_json=True,
        session_cookie_secure=True,
        cors_origins=["https://sga.institucion.gob"],
        trusted_hosts=["sga.institucion.gob"],
    )
    assert settings.environment is Environment.PRODUCTION


@pytest.mark.parametrize(
    "overrides",
    [
        {"debug": True},
        {"docs_enabled": True},
        {"log_json": False},
        {"session_cookie_secure": False},
        {"cors_origins": ["*"]},
        {"trusted_hosts": ["testserver"]},
    ],
)
def test_production_rejects_insecure_configuration(
    overrides: dict[str, object],
) -> None:
    base: dict[str, object] = {
        "environment": Environment.PRODUCTION,
        "debug": False,
        "docs_enabled": False,
        "log_json": True,
        "session_cookie_secure": True,
        "cors_origins": ["https://sga.institucion.gob"],
        "trusted_hosts": ["sga.institucion.gob"],
    }
    base.update(overrides)
    with pytest.raises(ValidationError):
        build_test_settings(**base)


def test_comma_separated_environment_lists(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SGA_ENVIRONMENT", "testing")
    monkeypatch.setenv("SGA_SECRET_KEY", "y" * 48)
    monkeypatch.setenv(
        "SGA_DATABASE_URL",
        "postgresql+psycopg://sga_test:sga_test@localhost:5432/sga_test",
    )
    monkeypatch.setenv("SGA_REDIS_URL", "redis://localhost:6379/15")
    monkeypatch.setenv("SGA_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    monkeypatch.setenv("SGA_TRUSTED_HOSTS", "localhost,127.0.0.1,testserver")
    monkeypatch.setenv("SGA_DOCS_ENABLED", "true")
    monkeypatch.setenv("SGA_LOG_JSON", "false")
    monkeypatch.setenv("SGA_SESSION_COOKIE_SECURE", "false")

    settings = Settings(_env_file=None)  # pyright: ignore[reportCallIssue]

    assert settings.cors_origins == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    assert settings.trusted_hosts == ["localhost", "127.0.0.1", "testserver"]
