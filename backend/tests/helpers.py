from __future__ import annotations

from typing import Any

from judicial_archive.core.config import Environment, Settings


def build_test_settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "environment": Environment.TESTING,
        "debug": False,
        "log_level": "WARNING",
        "log_json": False,
        "database_url": "postgresql+psycopg://sga:sga@localhost:5432/sga_test",
        "redis_url": "redis://localhost:6379/15",
        "secret_key": "test-secret-key-with-at-least-32-characters",
        "trusted_hosts": ["testserver", "localhost"],
        "cors_origins": ["http://localhost:5173"],
        "docs_enabled": True,
        "readiness_timeout_seconds": 0.5,
        "max_request_body_bytes": 1024 * 1024,
    }
    values.update(overrides)
    return Settings.model_validate(values)
