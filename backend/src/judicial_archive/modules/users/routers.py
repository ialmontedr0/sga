from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.api.deps import get_app_settings, get_session, require_permissions
from judicial_archive.core.config import Settings
from judicial_archive.modules.auth import schemas as auth_schemas, services as auth_services
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


@router.get("/{user_id}", response_model=schemas.UserDetail)
async def get_user(
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.USERS_READ)),
) -> dict[str, object]:
    return await services.get_user_detail(session, user_id)


@router.get("/{user_id}/sessions", response_model=list[auth_schemas.SessionInfo])
async def list_user_sessions(
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.SESSIONS_READ)),
) -> list[auth_schemas.SessionInfo]:
    return await auth_services.list_user_sessions(session, user_id)


@router.post(
    "/{user_id}/sessions/{session_id}/revoke",
    response_model=schemas.MessageResponse,
)
async def revoke_user_session(
    request: Request,
    user_id: UUID,
    session_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.SESSIONS_MANAGE)),
) -> dict[str, str]:
    return await auth_services.revoke_user_session(
        request, session, current_user, user_id, session_id
    )


@router.post("/{user_id}/reset-password", response_model=schemas.MessageResponse)
async def reset_password(
    request: Request,
    user_id: UUID,
    body: schemas.ResetPasswordRequest,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_app_settings),
    current_user: User = Depends(require_permissions(permissions.USERS_RESET_PASSWORD)),
) -> dict[str, str]:
    return await services.reset_password(request, session, settings, current_user, user_id, body)
