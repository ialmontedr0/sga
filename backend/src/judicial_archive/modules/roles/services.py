from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.core.enums import CatalogStatus
from judicial_archive.modules.auth.models import SecurityEvent
from judicial_archive.modules.roles import schemas
from judicial_archive.modules.roles.repositories import RolesRepository
from judicial_archive.modules.users.models import Permission, Role, User


async def list_roles(session: AsyncSession) -> list[dict[str, object]]:
    repo = RolesRepository(session)
    roles = await repo.list_roles()
    out: list[dict[str, object]] = []
    for role in roles:
        out.append(
            {
                "id": role.id,
                "code": role.code,
                "name": role.name,
                "description": role.description,
                "is_system": role.is_system,
                "status": role.status,
                "permissions": await repo.get_permission_codes_for_role(role.id),
            }
        )
    return out


async def create_role(
    request: Request,
    session: AsyncSession,
    actor: User,
    body: schemas.RoleCreate,
) -> dict[str, str]:
    repo = RolesRepository(session)
    code = body.code.strip().upper()
    if await repo.get_role_by_code(code):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El rol ya existe")

    role = Role(
        code=code,
        name=body.name.strip(),
        description=body.description.strip() if body.description else None,
        is_system=False,
        status=CatalogStatus.ACTIVE.value,
    )
    session.add(role)
    await session.flush()
    session.add(
        SecurityEvent(
            event_type="role_created",
            user_id=None,
            actor_id=actor.id,
            details={"role_code": role.code},
        )
    )
    await session.commit()
    return {"message": "Rol creado con exito."}


async def update_role(
    request: Request,
    session: AsyncSession,
    actor: User,
    role_id: UUID,
    body: schemas.RoleUpdate,
) -> dict[str, str]:
    repo = RolesRepository(session)
    role = await repo.get_role_by_id(role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol no encontrado")

    if role.is_system and body.status == CatalogStatus.INACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede desactivar un rol del sistema.",
        )

    changed: list[str] = []
    if body.name is not None:
        role.name = body.name.strip()
        changed.append("name")
    if body.description is not None:
        role.description = body.description.strip() or None
        changed.append("description")
    if body.status is not None:
        role.status = body.status
        changed.append("status")

    session.add(
        SecurityEvent(
            event_type="role_updated",
            user_id=None,
            actor_id=actor.id,
            details={"role_code": role.code, "fields": changed},
        )
    )
    await session.commit()
    return {"message": "Rol actualizado con exito."}


async def assign_permissions(
    request: Request,
    session: AsyncSession,
    actor: User,
    role_id: UUID,
    body: schemas.AssignPermissions,
) -> dict[str, str]:
    repo = RolesRepository(session)
    role = await repo.get_role_by_id(role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol no encontrado")

    if role.code == "ADMINISTRADOR":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "El rol Administador conserva el catalogo completo. "
                "Los permisos nuevos se aplican con el seed RBAC."
            ),
        )

    codes = sorted({code.strip().lower() for code in body.permission_codes if code.strip()})
    permissions = await repo.get_permissions_by_codes(codes)
    found = {permission.code for permission in permissions}
    unknown = sorted(set(codes) - found)
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Permisos desconocidos: {', '.join(unknown)}",
        )
    await repo.replace_role_permissions(
        role.id, [permission.id for permission in permissions], actor.id
    )

    session.add(
        SecurityEvent(
            event_type="role_permissions_updated",
            user_id=None,
            actor_id=actor.id,
            details={"role_code": role.code, permissions: codes},
        )
    )
    await session.commit()
    return {"message": "Permisos del rol actualizados con exito."}


async def list_permissions(session: AsyncSession) -> list[Permission]:
    repo = RolesRepository(session)
    return list(await repo.list_permissions())


async def create_permission(
    request: Request,
    session: AsyncSession,
    actor: User,
    body: schemas.PermissionCreate,
) -> dict[str, str]:
    repo = RolesRepository(session)
    code = body.code.strip().lower()
    if await repo.get_permission_by_code(code):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El permiso ya existe")

    permission = Permission(
        code=code,
        name=body.name.strip(),
        description=body.description.strip() if body.description else None,
    )
    session.add(permission)
    await session.flush()
    session.add(
        SecurityEvent(
            event_type="permission_created",
            user_id=None,
            actor_id=actor.id,
            details={"permission_code": permission.code},
        )
    )
    await session.commit()
    return {"message": "Permiso creado correctamente"}
