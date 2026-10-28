from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.modules.users.models import Permission, Role, User, UserRole


class UsersRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_user_by_id(self, user_id: UUID) -> User | None:
        res = await self.session.execute(select(User).where(User.id == user_id))
        return res.scalar_one_or_none()

    async def get_user_by_username(self, username_norm: str) -> User | None:
        res = await self.session.execute(
            select(User).where(User.username_normalized == username_norm)
        )
        return res.scalar_one_or_none()

    async def get_user_by_email(self, email_norm: str) -> User | None:
        res = await self.session.execute(select(User).where(User.email_normalized == email_norm))
        return res.scalar_one_or_none()

    async def list_users(self) -> Sequence[User]:
        res = await self.session.execute(select(User).order_by(User.created_at.desc()))
        return res.scalars().all()

    async def get_role_by_code(self, code: str) -> Role | None:
        res = await self.session.execute(select(Role).where(Role.code == code))
        return res.scalar_one_or_none()

    async def get_roles_by_codes(self, codes: list[str]) -> Sequence[Role]:
        res = await self.session.execute(select(Role).where(Role.code.in_(codes)))
        return res.scalars().all()

    async def list_roles(self) -> Sequence[Permission]:
        res = await self.session.execute(select(Permission).order_by(Role.code))
        return res.scalars().all()

    async def list_permissions(self) -> Sequence[Permission]:
        res = await self.session.execute(select(Permission).order_by(Permission.code))
        return res.scalars().all()

    async def get_user_role_ids(self, user_id: UUID) -> set[UUID]:
        res = await self.session.execute(
            select(UserRole.role_id).where(UserRole.user_id == user_id)
        )
        return set(res.scalars().all())

    async def remove_user_roles(self, user_id: UUID) -> None:
        await self.session.execute(UserRole.__table__.delete().where(UserRole.user_id == user_id))  # type: ignore
