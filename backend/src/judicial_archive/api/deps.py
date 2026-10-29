from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any, cast

from fastapi import Depends, HTTPException, Request, status
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.core.config import Settings
from judicial_archive.core.enums import UserStatus
from judicial_archive.core.security import hash_opaque_token, is_expired, verify_opaque_token
from judicial_archive.db.session import Database
from judicial_archive.modules.auth.models import AuthSession
from judicial_archive.modules.users.models import Permission, Role, RolePermission, User, UserRole


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


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_app_settings),
) -> User:
    cookie_name = settings.auth_session_cookie_name
    token = request.cookies.get(cookie_name)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado.")

    token_hash = hash_opaque_token(token)
    now = datetime.now(UTC)

    session_result = await session.execute(
        select(AuthSession).where(AuthSession.token_hash == token_hash)
    )
    auth_session = session_result.scalar_one_or_none()

    if not auth_session or auth_session.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesion invalida.")

    if is_expired(auth_session.expires_at) or is_expired(auth_session.absolute_expires_at):
        auth_session.revoked_at = now
        auth_session.revocation_reason = "expired"
        await session.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesion expirada.")

    user_result = await session.execute(select(User).where(User.id == auth_session.user_id))
    user_obj = user_result.scalar_one_or_none()

    if not user_obj:
        auth_session.revoked_at = now
        auth_session.revocation_reason = "user_missing"
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no autorizado"
        )

    if user_obj.status != UserStatus.ACTIVE.value:
        auth_session.revoked_at = now
        auth_session.revocation_reason = "user_inactive"
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no autorizado"
        )

    if user_obj.locked_until is not None and user_obj.locked_until > now:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Cuenta bloqueada")

    unsafe_methods = frozenset({"POST", "PUT", "PATCH", "DELETE"})
    if settings.auth_csrf_enabled and request.method.upper() in unsafe_methods:
        csrf_header = request.headers.get(settings.auth_csrf_header_name)
        if (
            not csrf_header
            or not auth_session.csrf_token_hash
            or not verify_opaque_token(csrf_header, auth_session.csrf_token_hash)
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token CSRF")

    # actualizar el last_seen_at
    auth_session.last_seen_at = now
    if user_obj.last_login_at is None:
        user_obj.last_login_at = now
    await session.commit()
    await session.refresh(user_obj)

    request.state.current_user = user_obj
    request.state.auth_session_id = auth_session.id
    return user_obj


def require_permissions(*required: str) -> Any:
    async def dependency(
        current_user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_session),
    ) -> User:
        if not required:
            return current_user

        stmt = (
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(Role, Role.id == RolePermission.role_id)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == current_user.id)
            .where(Role.status == "ACTIVE")
        )
        result = await session.execute(stmt)
        user_perms = {row[0] for row in result.all()}

        for p in required:
            if p not in user_perms:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Permisos insuficientes",
                )
        return current_user

    return dependency


def require_roles(*required: str) -> Any:
    async def dependency(
        current_user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_session),
    ) -> User:
        if not required:
            return current_user
        stmt = (
            select(Role.code)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == current_user.id)
            .where(Role.status == "ACTIVE")
        )
        result = await session.execute(stmt)
        user_roles = {row[0] for row in result.all()}
        for r in required:
            if r not in user_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail="Rol insuficiente"
                )
        return current_user

    return dependency
