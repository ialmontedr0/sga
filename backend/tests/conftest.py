from __future__ import annotations

from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from judicial_archive.main import create_app
from tests.helpers import build_test_settings


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    app = create_app(build_test_settings(), configure_logs=False)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as http_client:
        yield http_client
