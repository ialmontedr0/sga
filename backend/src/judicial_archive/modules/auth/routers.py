from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.api.deps import get_app_settings, get_current_user, get_session
from judicial_archive.core.config import Settings
from judicial_archive.modules.auth import schemas, services
from judicial_archive.modules.users.models import User

router = APIRouter(prefix="/auth", tags=["Autenticacion"])


@router.post("/login", response_model=schemas.MessageResponse)
async def login(
    request: Request,
    body: schemas.LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_app_settings),
) -> dict[str, str]:
    return await services.login(request, response, session, settings, body)


@router.post("/logout", response_model=schemas.MessageResponse)
async def logout(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_app_settings),
) -> dict[str, str]:
    return await services.logout(request, response, session, settings, current_user)


@router.post("/logout-all", response_model=schemas.MessageResponse)
async def logout_all(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_app_settings),
) -> dict[str, str]:
    return await services.logout_all(request, response, session, settings, current_user)


@router.get("/me", response_model=schemas.UserMe)
async def me(
    current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)
) -> schemas.UserMe:
    return await services.get_me(session, current_user)


@router.post("/change-password", response_model=schemas.MessageResponse)
async def change_password(
    request: Request,
    response: Response,
    body: schemas.ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_app_settings),
) -> dict[str, str]:
    return await services.change_password(request, response, session, settings, current_user, body)
