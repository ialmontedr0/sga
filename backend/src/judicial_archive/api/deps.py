from __future__ import annotations

from collections.abc import AsyncIterator
from typing import cast

from fastapi import Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.core.config import Settings
from judicial_archive.db.session import Database


def get_app_settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


def get_database(request: Request) -> Database:
    return cast(Database, request.app.state.database)


def get_redis(request: Request) -> Redis:
    return cast(Redis, request.app.state.redis)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Entrega una sesion por peticion. El servicio define commit/rollback"""
    database = get_database(request)
    async with database.session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
