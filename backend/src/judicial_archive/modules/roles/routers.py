from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.api.deps import get_session, require_permissions
from judicial_archive.modules.roles import schemas, services
from judicial_archive.modules.users import permissions
from judicial_archive.modules.users.models import Permission, User

router = APIRouter(prefix="/roles", tags=["Roles"])
permissions_router = APIRouter(prefix="/permissions", tags=["Permisos"])


# Rutas
@router.get("/", response_model=list[schemas.RoleOut])
async def list_roles(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.ROLES_READ)),
) -> list[dict[str, object]]:
    return await services.list_roles(session)


@router.post("/", response_model=schemas.MessageResponse)
async def create_role(
    request: Request,
    body: schemas.RoleCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.ROLES_MANAGE)),
) -> dict[str, str]:
    return await services.create_role(request, session, current_user, body)


@router.patch("/{role_id}", response_model=schemas.MessageResponse)
async def update_role(
    request: Request,
    role_id: UUID,
    body: schemas.RoleUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.ROLES_MANAGE)),
) -> dict[str, str]:
    return await services.update_role(request, session, current_user, role_id, body)


@router.post("/{role_id}/permissions", response_model=schemas.MessageResponse)
async def assign_permissions(
    request: Request,
    role_id: UUID,
    body: schemas.AssignPermissions,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.ROLES_MANAGE)),
) -> dict[str, str]:
    return await services.assign_permissions(request, session, current_user, role_id, body)


@permissions_router.get("/", response_model=list[schemas.PermissionOut])
async def list_permissions(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.PERMISSIONS_READ)),
) -> list[Permission]:
    return await services.list_permissions(session)


@permissions_router.post("/", response_model=schemas.MessageResponse)
async def create_permission(
    request: Request,
    body: schemas.PermissionCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.PERMISSIONS_MANAGE)),
) -> dict[str, str]:
    return await services.create_permission(request, session, current_user, body)
