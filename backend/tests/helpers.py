from __future__ import annotations

import os
from typing import Any

from judicial_archive.core.config import Environment, Settings


def build_test_settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "environment": Environment.TESTING,
        "debug": False,
        "log_level": "WARNING",
        "log_json": False,
        "database_url": os.environ.get("TEST_DATABASE_URL")
        or "postgresql+psycopg://sga:sga@localhost:5432/sga_test",
        "redis_url": os.environ.get("TEST_REDIS_URL") or "redis://localhost:6379/15",
        "secret_key": "test-secret-key-with-at-least-32-characters",
        "trusted_hosts": ["testserver", "localhost"],
        "cors_origins": ["http://localhost:5173"],
        "docs_enabled": True,
        "readiness_timeout_seconds": 0.5,
        "max_request_body_bytes": 1024 * 1024,
        "auth_session_cookie_secure": False,
        "auth_csrf_cookie_secure": False,
        "auth_csrf_enabled": True,
    }
    values.update(overrides)
    if values.get("environment") == Environment.PRODUCTION:
        values["auth_session_cookie_secure"] = True
        values["auth_csrf_cookie_secure"] = True
    return Settings.model_validate(values)
