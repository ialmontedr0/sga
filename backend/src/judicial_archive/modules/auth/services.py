from __future__ import annotations

from datetime import UTC, datetime, timedelta
from ipaddress import ip_address
from uuid import UUID

from fastapi import HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.core.config import Settings
from judicial_archive.core.enums import UserStatus
from judicial_archive.core.security import (
    compute_session_expiry,
    generate_csrf_token,
    generate_session_token,
    hash_opaque_token,
    hash_password,
    verify_password,
)
from judicial_archive.modules.auth.models import AuthSession, LoginAttempt, SecurityEvent
from judicial_archive.modules.auth.repositories import AuthRepository
from judicial_archive.modules.auth.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    SessionInfo,
    UserMe,
)
from judicial_archive.modules.users.models import Permission, Role, RolePermission, User, UserRole


def _get_client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # Tomar primera IP
        ip = forwarded.split(",")[0].strip()
        try:
            ip_address(ip)
            return ip
        except Exception:  # noqa: S110
            pass
    if request.client and request.client.host:
        try:
            ip_address(request.client.host)
            return request.client.host
        except Exception:  # noqa: S110
            pass
    return None


def _get_user_agent(request: Request) -> str | None:
    ua = request.headers.get("user-agent")
    if not ua:
        return None
    return ua[:512]


async def list_user_sessions(
    session: AsyncSession,
    user_id: UUID,
) -> list[SessionInfo]:
    res = await session.execute(
        select(AuthSession)
        .where(
            AuthSession.user_id == user_id,
            AuthSession.revoked_at.is_(None),
        )
        .order_by(AuthSession.created_at.desc())
    )
    return [
        SessionInfo(
            id=auth_session.id,
            created_at=auth_session.created_at,
            last_seen_at=auth_session.last_seen_at,
            expires_at=auth_session.expires_at,
            ip_address=str(auth_session.ip_address) if auth_session.ip_address else None,
            user_agent=auth_session.user_agent,
        )
        for auth_session in res.scalars().all()
    ]


def set_csrf_cookie(response: Response, settings: Settings, token: str) -> None:
    response.set_cookie(
        key=settings.auth_csrf_cookie_name,
        value=token,
        httponly=settings.auth_csrf_cookie_httponly,
        secure=settings.auth_csrf_cookie_secure,
        samesite=settings.auth_csrf_cookie_samesite,
        path=settings.auth_csrf_cookie_path,
        max_age=settings.auth_csrf_max_age_seconds,
    )


def _set_session_cookies(
    response: Response, settings: Settings, session_token: str, csrf_token: str
) -> None:
    response.set_cookie(
        key=settings.auth_session_cookie_name,
        value=session_token,
        httponly=settings.auth_session_cookie_httponly,
        secure=settings.auth_session_cookie_secure,
        samesite=settings.auth_session_cookie_samesite,
        path=settings.auth_session_cookie_path,
        max_age=settings.auth_session_max_age_seconds,
    )
    set_csrf_cookie(response, settings, csrf_token)


def _clear_session_cookies(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.auth_session_cookie_name,
        path=settings.auth_session_cookie_path,
        samesite=settings.auth_session_cookie_samesite,
        secure=settings.auth_session_cookie_secure,
        httponly=settings.auth_session_cookie_httponly,
    )
    response.delete_cookie(
        key=settings.auth_csrf_cookie_name,
        path=settings.auth_csrf_cookie_path,
        samesite=settings.auth_csrf_cookie_samesite,
        secure=settings.auth_csrf_cookie_secure,
        httponly=settings.auth_csrf_cookie_httponly,
    )


async def _get_user_roles_and_permissions(
    session: AsyncSession, user_id: UUID
) -> tuple[list[str], list[str]]:
    roles_res = await session.execute(
        select(Role.code)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user_id)
        .where(Role.status == "ACTIVE")
    )
    roles = [row[0] for row in roles_res.all()]

    perms_res = await session.execute(
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(Role, Role.id == RolePermission.role_id)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user_id)
        .where(Role.status == "ACTIVE")
        .distinct()
    )
    perms = [row[0] for row in perms_res.all()]
    return roles, perms


async def login(
    request: Request,
    response: Response,
    session: AsyncSession,
    settings: Settings,
    body: LoginRequest,
) -> dict[str, str]:
    repo = AuthRepository(session)
    username_norm = body.username.lower().strip()
    client_ip = _get_client_ip(request)
    user_agent = _get_user_agent(request)
    now = datetime.now(UTC)

    user = await repo.get_user_by_username(body.username)

    # Registrar intento fallido genérico
    async def _log_fail(reason: str) -> None:
        await repo.log_attempt(
            LoginAttempt(
                username=body.username.strip()[:64],
                username_normalized=username_norm,
                ip_address=client_ip,
                user_agent=user_agent,
                success=False,
                reason=reason,
            )
        )
        await repo.log_security_event(
            SecurityEvent(
                event_type="login_failed",
                user_id=user.id if user else None,
                actor_id=None,
                ip_address=client_ip,
                user_agent=user_agent,
                details={"username": username_norm, "reason": reason},
            )
        )

    if not user:
        await _log_fail("unknown_user")
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas"
        )

    # Verificar bloqueo
    if user.locked_until and user.locked_until > now:
        await _log_fail("locked")
        await session.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Cuenta bloqueada")

    # Verificar estado
    if user.status != UserStatus.ACTIVE.value:
        await _log_fail("inactive")
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas"
        )

    # Contar intentos fallidos recientes
    since = now - timedelta(minutes=settings.auth_login_window_minutes)
    await repo.count_recent_failed(username_norm, since)

    # Verificar contraseña
    if not verify_password(body.password, user.password_hash):
        user.failed_login_count = (user.failed_login_count or 0) + 1
        if user.failed_login_count >= settings.auth_login_max_attempts:
            user.locked_until = now + timedelta(minutes=settings.auth_login_lockout_minutes)
        await _log_fail("bad_password")
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas"
        )

    # Login exitoso
    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = now
    if not user.password_changed_at:
        user.password_changed_at = now

    csrf_token = request.cookies.get(settings.auth_csrf_cookie_name)
    if settings.auth_csrf_enabled and not csrf_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token CSRF ausente")
    if not csrf_token:
        csrf_token = generate_csrf_token()

    session_token = generate_session_token()
    token_hash = hash_opaque_token(session_token)
    csrf_hash = hash_opaque_token(csrf_token)

    expires_at, absolute_expires_at = compute_session_expiry(
        settings.auth_session_idle_minutes, settings.auth_session_absolute_hours
    )

    auth_sess = AuthSession(
        user_id=user.id,
        token_hash=token_hash,
        csrf_token_hash=csrf_hash,
        user_agent=user_agent,
        ip_address=client_ip,
        expires_at=expires_at,
        absolute_expires_at=absolute_expires_at,
    )
    await repo.create_session(auth_sess)

    await repo.log_attempt(
        LoginAttempt(
            username=user.username,
            username_normalized=username_norm,
            ip_address=client_ip,
            user_agent=user_agent,
            success=True,
            reason=None,
        )
    )
    await repo.log_security_event(
        SecurityEvent(
            event_type="login_success",
            user_id=user.id,
            actor_id=user.id,
            ip_address=client_ip,
            user_agent=user_agent,
            details={"session_id": str(auth_sess.id)},
        )
    )

    _set_session_cookies(response, settings, session_token, csrf_token)
    await session.commit()
    return {"message": "Inicio de sesión correcto"}


async def logout(
    request: Request,
    response: Response,
    session: AsyncSession,
    settings: Settings,
    current_user: User,
) -> dict[str, str]:
    repo = AuthRepository(session)
    auth_session_id = getattr(request.state, "auth_session_id", None)
    client_ip = _get_client_ip(request)
    user_agent = _get_user_agent(request)

    if auth_session_id:
        await repo.revoke_session(auth_session_id, current_user.id, "logout")

    await repo.log_security_event(
        SecurityEvent(
            event_type="logout",
            user_id=current_user.id,
            actor_id=current_user.id,
            ip_address=client_ip,
            user_agent=user_agent,
            details={"session_id": str(auth_session_id) if auth_session_id else None},
        )
    )

    _clear_session_cookies(response, settings)
    await session.commit()
    return {"message": "Sesión cerrada"}


async def logout_all(
    request: Request,
    response: Response,
    session: AsyncSession,
    settings: Settings,
    current_user: User,
) -> dict[str, str]:
    repo = AuthRepository(session)
    getattr(request.state, "auth_session_id", None)
    client_ip = _get_client_ip(request)
    user_agent = _get_user_agent(request)

    await repo.revoke_all_user_sessions(
        current_user.id, current_user.id, "logout_all", except_session_id=None
    )

    await repo.log_security_event(
        SecurityEvent(
            event_type="session_revoked_all",
            user_id=current_user.id,
            actor_id=current_user.id,
            ip_address=client_ip,
            user_agent=user_agent,
            details={},
        )
    )

    _clear_session_cookies(response, settings)
    await session.commit()
    return {"message": "Todas las sesiones han sido cerradas"}


async def revoke_user_session(
    request: Request, session: AsyncSession, actor: User, user_id: UUID, session_id: UUID
) -> dict[str, str]:
    res = await session.execute(
        select(AuthSession).where(AuthSession.id == session_id, AuthSession.user_id == user_id)
    )
    target = res.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sesion no encontrada")

    if target.revoked_at is None:
        target.revoked_at = datetime.now(UTC)
        target.revoked_by = actor.id
        target.revocation_reason = "revoked_by_admin"

    session.add(
        SecurityEvent(
            event_type="session_revoked_by_admin",
            user_id=user_id,
            actor_id=actor.id,
            details={"session_id": str(session_id)},
        )
    )
    await session.commit()
    return {"message": "Sesion revocada correctamente"}


async def get_me(session: AsyncSession, current_user: User) -> UserMe:
    roles, perms = await _get_user_roles_and_permissions(session, current_user.id)
    return UserMe(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        display_name=current_user.display_name,
        status=current_user.status,
        must_change_password=current_user.must_change_password,
        roles=roles,
        permissions=perms,
    )


async def change_password(
    request: Request,
    response: Response,
    session: AsyncSession,
    settings: Settings,
    current_user: User,
    body: ChangePasswordRequest,
) -> dict[str, str]:
    repo = AuthRepository(session)
    client_ip = _get_client_ip(request)
    user_agent = _get_user_agent(request)
    now = datetime.now(UTC)

    if not verify_password(body.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Contraseña actual incorrecta"
        )

    if len(body.new_password) < settings.auth_password_min_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La nueva contraseña debe tener al menos {settings.auth_password_min_length} caracteres",
        )

    if verify_password(body.new_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La nueva contraseña debe ser diferente a la actual",
        )

    current_user.password_hash = hash_password(body.new_password)
    current_user.password_changed_at = now
    current_user.must_change_password = False
    current_user.failed_login_count = 0
    current_user.locked_until = None

    auth_session_id = getattr(request.state, "auth_session_id", None)
    await repo.revoke_all_user_sessions(
        current_user.id, current_user.id, "password_changed", except_session_id=auth_session_id
    )

    await repo.log_security_event(
        SecurityEvent(
            event_type="password_changed",
            user_id=current_user.id,
            actor_id=current_user.id,
            ip_address=client_ip,
            user_agent=user_agent,
            details={},
        )
    )

    await session.commit()
    return {"message": "Contraseña actualizada correctamente"}
