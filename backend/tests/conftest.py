from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from judicial_archive.core.config import Settings
from judicial_archive.main import create_app
from tests.helpers import build_test_settings


@pytest.fixture
def settings() -> Settings:
    return build_test_settings()


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    app = create_app(settings, configure_logs=False)
    with TestClient(app) as test_client:
        yield test_client
