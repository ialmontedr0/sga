from __future__ import annotations

from typing import Any

from judicial_archive.core.config import Environment, Settings


def build_test_settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "environment": Environment.TESTING,
        "debug": False,
        "secret_key": "x" * 48,
        "database_url": "postgresql+psycopg://sga_test:sga_test@localhost:5432/sga_test",
        "redis_url": "redis://localhost:6379/15",
        "cors_origins": ["http://localhost:5173"],
        "trusted_hosts": ["testserver", "localhost", "127.0.0.1"],
        "docs_enabled": True,
        "log_json": False,
        "session_cookie_secure": False,
        "storage_root": "var/storage",
    }
    values.update(overrides)
    return Settings.model_validate(values)
