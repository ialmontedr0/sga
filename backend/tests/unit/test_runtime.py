from __future__ import annotations

import asyncio

from judicial_archive.core.runtime import selector_loop_factory


def test_selector_loop_factory_returns_selector_loop() -> None:
    loop = selector_loop_factory()

    try:
        assert isinstance(loop, asyncio.SelectorEventLoop)
    finally:
        loop.close()
