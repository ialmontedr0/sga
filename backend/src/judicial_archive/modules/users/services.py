from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.core.enums import UserStatus
from judicial_archive.core.security import hash_password
from judicial_archive.modules.auth.models import SecurityEvent
from judicial_archive.modules.users.models import Role, User, UserRole
from judicial_archive.modules.users.repositories import UsersRepository
from judicial_archive.modules.users.schemas import UserCreate, UserUpdate


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
        roles = await repo.get_roles_by_codes([r.upper() for r in body.role_codes])
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
    roles = await repo.get_roles_by_codes([r.upper() for r in role_codes])
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
