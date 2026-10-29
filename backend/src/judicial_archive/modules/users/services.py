from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.core.config import Settings
from judicial_archive.core.enums import UserStatus
from judicial_archive.core.security import hash_password
from judicial_archive.modules.auth.models import SecurityEvent
from judicial_archive.modules.auth.repositories import AuthRepository
from judicial_archive.modules.users.models import Role, User, UserRole
from judicial_archive.modules.users.repositories import UsersRepository
from judicial_archive.modules.users.schemas import ResetPasswordRequest, UserCreate, UserUpdate


async def list_users(session: AsyncSession) -> list[dict[str, object]]:
    repo = UsersRepository(session)
    users = await repo.list_users()
    out = []
    for u in users:
        roles_res = await session.execute(
            select(Role.code).join(UserRole).where(UserRole.user_id == u.id)
        )
        out.append(
            {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "display_name": u.display_name,
                "status": u.status,
                "must_change_password": u.must_change_password,
                "failed_login_count": u.failed_login_count,
                "locked_until": u.locked_until,
                "last_login_at": u.last_login_at,
                "created_at": u.created_at,
                "roles": [r[0] for r in roles_res.all()],
            }
        )
    return out


async def get_user_detail(
    session: AsyncSession,
    user_id: UUID,
) -> dict[str, object]:
    repo = UsersRepository(session)
    user = await repo.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "display_name": user.display_name,
        "status": user.status,
        "must_change_password": user.must_change_password,
        "failed_login_count": user.failed_login_count,
        "locked_until": user.locked_until,
        "last_login_at": user.last_login_at,
        "created_at": user.created_at,
        "roles": await repo.get_role_codes(user.id),
        "permissions": await repo.get_permission_codes(user.id),
    }


async def create_user(
    request: Request, session: AsyncSession, actor: User, body: UserCreate
) -> dict[str, str]:
    repo = UsersRepository(session)
    username_norm = body.username.lower().strip()
    if await repo.get_user_by_username(username_norm):
        raise HTTPException(status_code=409, detail="El nombre de usuario ya existe")
    if body.email:
        email_norm = body.email.lower().strip()
        if await repo.get_user_by_email(email_norm):
            raise HTTPException(status_code=409, detail="El email ya existe")

    user = User(
        username=body.username.strip(),
        username_normalized=username_norm,
        email=body.email,
        email_normalized=body.email.lower().strip() if body.email else None,
        display_name=body.display_name.strip(),
        password_hash=hash_password(body.password),
        status=UserStatus.ACTIVE.value,
        must_change_password=body.must_change_password,
        failed_login_count=0,
    )
    session.add(user)
    await session.flush()

    if body.role_codes:
        normalized = sorted({code.strip().upper() for code in body.role_codes})
        roles = await repo.get_roles_by_codes(normalized)
        found = {role.code for role in roles}
        unknown = sorted(set(normalized) - found)
        if unknown:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Roles desconocidos: {', '.join(unknown)}",
            )
        for role in roles:
            session.add(UserRole(user_id=user.id, role_id=role.id, assigned_by=actor.id))

    session.add(
        SecurityEvent(
            event_type="user_created",
            user_id=user.id,
            actor_id=actor.id,
            details={"username": user.username},
        )
    )
    await session.commit()
    await session.refresh(user)
    return {"message": "Usuario creado correctamente"}


async def update_user(
    request: Request, session: AsyncSession, actor: User, user_id: UUID, body: UserUpdate
) -> dict[str, str]:
    repo = UsersRepository(session)
    user = await repo.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if body.email is not None:
        email_norm = body.email.lower().strip()
        existing = await repo.get_user_by_email(email_norm)
        if existing and existing.id != user.id:
            raise HTTPException(status_code=409, detail="El email ya existe")
        user.email = body.email
        user.email_normalized = email_norm

    if body.display_name is not None:
        user.display_name = body.display_name.strip()
    if body.status is not None:
        user.status = body.status
    if body.status == "INACTIVE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes desactivar tu cuenta en este momento",
        )
    if body.status == "SUSPENDED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes desactivar tu cuenta en este momento",
        )
    if body.status == "LOCKED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes desactivar tu cuenta en este momento",
        )
    if body.must_change_password is not None:
        user.must_change_password = body.must_change_password

    session.add(
        SecurityEvent(event_type="user_updated", user_id=user.id, actor_id=actor.id, details={})
    )
    await session.commit()
    return {"message": "Usuario actualizado correctamente"}


async def lock_user(
    request: Request, session: AsyncSession, actor: User, user_id: UUID, lock: bool
) -> dict[str, str]:
    repo = UsersRepository(session)
    user = await repo.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if lock:
        user.status = UserStatus.LOCKED.value
        user.locked_until = datetime.now(UTC).replace(year=9999)
    else:
        user.status = UserStatus.ACTIVE.value
        user.locked_until = None
        user.failed_login_count = 0

    if actor.id == user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No puedes bloquear tu propia cuenta"
        )

    session.add(
        SecurityEvent(
            event_type="user_locked" if lock else "user_unlocked",
            user_id=user.id,
            actor_id=actor.id,
            details={},
        )
    )
    await session.commit()
    return {"message": "Usuario bloqueado" if lock else "Usuario desbloqueado"}


async def assign_roles(
    request: Request, session: AsyncSession, actor: User, user_id: UUID, role_codes: list[str]
) -> dict[str, str]:
    repo = UsersRepository(session)
    user = await repo.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    await repo.remove_user_roles(user_id)

    normalized = sorted({code.strip().upper() for code in role_codes})
    roles = await repo.get_roles_by_codes(normalized)
    found = {role.code for role in roles}
    unknown = sorted(set(normalized) - found)
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Roles desconocidos: {', '.join(unknown)}",
        )

    if actor.id == user_id and "ADMINISTRADOR" not in found:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes retirarte de tu propio rol de Administrador.",
        )

    for role in roles:
        session.add(UserRole(user_id=user.id, role_id=role.id, assigned_by=actor.id))
    session.add(
        SecurityEvent(
            event_type="roles_assigned",
            user_id=user.id,
            actor_id=actor.id,
            details={"roles": [r.code for r in roles]},
        )
    )
    await session.commit()
    return {"message": "Roles asignados correctamente"}


## Restablecer contrase;a
async def reset_password(
    request: Request,
    session: AsyncSession,
    settings: Settings,
    actor: User,
    user_id: UUID,
    body: ResetPasswordRequest,
) -> dict[str, str]:
    """Restablecimiento de contrasena

    Args:
        request (Request): _description_
        session (AsyncSession): _description_
        settings (Settings): _description_
        actor (User): _description_
        user_id (UUID): _description_
        body (ResetPasswordRequest): _description_

    Returns:
        dict[str, str]: _description_
    """
    repo = UsersRepository(session)
    user = await repo.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    if len(body.new_password) < settings.auth_password_min_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "La nueva contrasena debe tener al menos "
                f"{settings.auth_password_min_length} caracteres"
            ),
        )

    user.password_hash = hash_password(body.new_password)
    user.password_changed_at = datetime.now(UTC)
    user.must_change_password = body.must_change_password
    user.failed_login_count = 0
    user.locked_until = None

    await AuthRepository(session).revoke_all_user_sessions(
        user.id, actor.id, "password_reset_by_admin"
    )
    session.add(
        SecurityEvent(
            event_type="password_reset_by_admin",
            user_id=user.id,
            actor_id=actor.id,
            details={"must_change_password": body.must_change_password},
        )
    )

    await session.commit()
    return {"message": "Contrasena restablecida con exito."}
