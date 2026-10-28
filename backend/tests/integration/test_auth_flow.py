from __future__ import annotations

import os

import pytest


@pytest.mark.integration
async def test_auth_flow_placeholder() -> None:
    if os.getenv("RUN_INTEGRATION") != "1":
        pytest.skip("RUN_INTEGRATION!=1")
    # Placeholder - requiere BD de pruebas configurada
    assert True
