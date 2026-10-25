from __future__ import annotations

import asyncio
import sys


def configure_event_loop_policy() -> None:
    """Usa SelectorEventLoop en Windows para compatibilidad con psycopg async."""
    if sys.platform != "win32":
        return

    from asyncio.windows_events import WindowsSelectorEventLoopPolicy

    asyncio.set_event_loop_policy(  # pyright: ignore[reportDeprecated]
        WindowsSelectorEventLoopPolicy()
    )
