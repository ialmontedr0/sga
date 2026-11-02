from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.api.deps import get_session, require_permissions
from judicial_archive.core.pagination import Page, PageParams, pagination_params
from judicial_archive.modules.settings import schemas, services
from judicial_archive.modules.users import permissions
from judicial_archive.modules.users.models import User

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=Page[schemas.SettingOut])
async def list_settings(
    params: Annotated[PageParams, Depends(pagination_params)],
    q: Annotated[str | None, Query(max_length=100)] = None,
    value_type: Annotated[str | None, Query()] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.SETTINGS_READ)),
) -> Page[schemas.SettingOut]:
    return await services.list_settings(
        session,
        params=params,
        q=q,
        value_type=value_type,
    )


@router.get("/{key}", response_model=schemas.SettingOut)
async def get_setting(
    key: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.SETTINGS_READ)),
) -> schemas.SettingOut:
    return await services.get_setting(session, key)


@router.put("/{key}", response_model=schemas.SettingOut)
async def upsert_setting(
    request: Request,
    key: str,
    body: schemas.SettingUpsert,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.SETTINGS_MANAGE)),
) -> schemas.SettingOut:
    return await services.upsert_setting(request, session, current_user, key, body)
