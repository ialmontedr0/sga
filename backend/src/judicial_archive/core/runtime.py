from __future__ import annotations

import asyncio
import os


def configure_event_loop_policy() -> None:
    """Usa SelectorEventLoop en Windows para compatibilidad con psycopg async."""
    if os.name != "nt":
        return

    policy_type = getattr(asyncio, "WindowsSelectorEventLoopPolicy", None)
    if policy_type is not None:
        asyncio.set_event_loop_policy(  # pyright: ignore[reportDeprecated]
            policy_type()
        )


def selector_loop_factory() -> asyncio.AbstractEventLoop:
    """Fabrica de loop para uvicorn en Windows; psycopg no usa Proactor."""
    return asyncio.SelectorEventLoop()
