from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.api.deps import get_session, require_permissions
from judicial_archive.modules.users import permissions, schemas, services
from judicial_archive.modules.users.models import User

router = APIRouter(prefix="/users", tags=["Usuarios"])


@router.get("/", response_model=list[schemas.UserOut])
async def list_users(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.USERS_READ)),
) -> list[dict[str, object]]:
    return await services.list_users(session)


@router.post("/", response_model=schemas.MessageResponse)
async def create_user(
    request: Request,
    body: schemas.UserCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.USERS_CREATE)),
) -> dict[str, str]:
    return await services.create_user(request, session, current_user, body)


@router.patch("/{user_id}", response_model=schemas.MessageResponse)
async def update_user(
    request: Request,
    user_id: UUID,
    body: schemas.UserUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.USERS_UPDATE)),
) -> dict[str, str]:
    return await services.update_user(request, session, current_user, user_id, body)


@router.post("/{user_id}/lock", response_model=schemas.MessageResponse)
async def lock_user(
    request: Request,
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.USERS_LOCK)),
) -> dict[str, str]:
    return await services.lock_user(request, session, current_user, user_id, True)


@router.post("/{user_id}/unlock", response_model=schemas.MessageResponse)
async def unlock_user(
    request: Request,
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.USERS_LOCK)),
) -> dict[str, str]:
    return await services.lock_user(request, session, current_user, user_id, False)


@router.post("/{user_id}/roles", response_model=schemas.MessageResponse)
async def assign_roles(
    request: Request,
    user_id: UUID,
    body: schemas.AssignRoles,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.ROLES_MANAGE)),
) -> dict[str, str]:
    return await services.assign_roles(request, session, current_user, user_id, body.role_codes)
