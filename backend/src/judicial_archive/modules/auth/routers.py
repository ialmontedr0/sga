from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.api.deps import get_app_settings, get_current_user, get_session
from judicial_archive.core.config import Settings
from judicial_archive.core.security import generate_csrf_token
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


@router.get("/csrf", response_model=schemas.CsrfTokenResponse)
async def csrf_token(
    request: Request,
    response: Response,
    settings: Settings = Depends(get_app_settings),
) -> schemas.CsrfTokenResponse:
    # No rotar un token existente: la sesion ya tiene su hash vinculado y rotarlo invalidaria los POST de un cliente autenticado.
    token = request.cookies.get(settings.auth_csrf_cookie_name)
    if not token or len(token) < 32:
        token = generate_csrf_token()
        services.set_csrf_cookie(response, settings, token)
    return schemas.CsrfTokenResponse(csrf_token=token)


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
