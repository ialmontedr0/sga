from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.modules.users.models import Permission, Role, RolePermission


class RolesRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_roles(self) -> Sequence[Role]:
        res = await self.session.execute(select(Role).order_by(Role.code))
        return res.scalars().all()

    async def get_role_by_id(self, role_id: UUID) -> Role | None:
        res = await self.session.execute(select(Role).where(Role.id == role_id))
        return res.scalar_one_or_none()

    async def get_role_by_code(self, code: str) -> Role | None:
        res = await self.session.execute(select(Role).where(Role.code == code))
        return res.scalar_one_or_none()

    async def list_permissions(self) -> Sequence[Permission]:
        res = await self.session.execute(select(Permission).order_by(Permission.code))
        return res.scalars().all()

    async def get_permission_by_code(self, code: str) -> Permission | None:
        res = await self.session.execute(select(Permission).where(Permission.code == code))
        return res.scalar_one_or_none()

    async def get_permissions_by_codes(self, codes: list[str]) -> Sequence[Permission]:
        if not codes:
            return []
        res = await self.session.execute(select(Permission).where(Permission.code.in_(codes)))
        return res.scalars().all()

    async def get_permission_codes_for_role(self, role_id: UUID) -> list[str]:
        res = await self.session.execute(
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id == role_id)
            .order_by(Permission.code)
        )
        return [row[0] for row in res.all()]

    async def replace_role_permissions(
        self,
        role_id: UUID,
        permission_ids: list[UUID],
        granted_by: UUID | None,
    ) -> None:
        await self.session.execute(delete(RolePermission).where(RolePermission.role_id == role_id))
        await self.session.flush()
        for permission_id in permission_ids:
            self.session.add(
                RolePermission(role_id=role_id, permission_id=permission_id, granted_by=granted_by)
            )
