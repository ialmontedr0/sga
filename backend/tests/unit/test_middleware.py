from __future__ import annotations

import pytest
from starlette.types import Receive, Scope, Send

from judicial_archive.core.middleware import TrustedHostMiddleware


async def _app(scope: Scope, receive: Receive, send: Send) -> None:
    raise AssertionError("La peticion no deberia llegar a la aplicacion")


@pytest.mark.parametrize("pattern", ["foo*bar", "*example.com"])
def test_trusted_host_rejects_invalid_wildcards(pattern: str) -> None:
    with pytest.raises(ValueError, match="comodin"):
        TrustedHostMiddleware(_app, allowed_hosts=[pattern])
