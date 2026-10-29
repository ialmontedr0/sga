from __future__ import annotations

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.db.seed_rbac import (
    PERMISSIONS,
    ROLE_PERMISSIONS,
    seed_rbac,
)
from judicial_archive.modules.users.models import Permission, Role, RolePermission


async def _count(session: AsyncSession, model: type[object]) -> int:
    value = await session.scalar(select(func.count()).select_from(model))
    return int(value or 0)


@pytest.mark.integration
async def test_seed_rbac_is_idempotent(db_session: AsyncSession) -> None:
    await seed_rbac(db_session)
    await db_session.commit()

    permissions = await _count(db_session, Permission)
    links = await _count(db_session, RolePermission)
    roles = await _count(db_session, Role)

    assert permissions == len(PERMISSIONS)
    assert links == sum(len(codes) for codes in ROLE_PERMISSIONS.values())
    assert roles == len(ROLE_PERMISSIONS)

    await seed_rbac(db_session)
    await db_session.commit()

    assert await _count(db_session, Permission) == permissions
    assert await _count(db_session, RolePermission) == links
    assert await _count(db_session, Role) == roles


@pytest.mark.integration
async def test_administrator_has_all_permissions(db_session: AsyncSession) -> None:
    await seed_rbac(db_session)
    await db_session.commit()

    result = await db_session.execute(
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(Role, Role.id == RolePermission.role_id)
        .where(Role.code == "ADMINISTRADOR")
    )
    admin_codes = set(result.scalars().all())
    assert admin_codes == {code for code, _, _ in PERMISSIONS}


@pytest.mark.integration
async def test_no_duplicate_role_permissions(db_session: AsyncSession) -> None:
    await seed_rbac(db_session)
    await db_session.commit()

    result = await db_session.execute(
        select(RolePermission.role_id, RolePermission.permission_id)
        .group_by(RolePermission.role_id, RolePermission.permission_id)
        .having(func.count() > 1)
    )
    assert result.all() == []
