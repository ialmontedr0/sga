from __future__ import annotations

from fastapi import Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.core.errors import ConflictError, InvalidParameterError, NotFoundError
from judicial_archive.core.pagination import Page, PageParams
from judicial_archive.core.text import ensure_setting_key
from judicial_archive.modules.audit.services import record_audit_event
from judicial_archive.modules.courts.models import SystemSetting
from judicial_archive.modules.settings import schemas
from judicial_archive.modules.settings.repositores import SettingsRepository
from judicial_archive.modules.settings.validations import validate_setting_value
from judicial_archive.modules.users.models import User


def _snapshot(item: SystemSetting) -> dict[str, object]:
    return {
        "key": item.key,
        "value": item.value,
        "value_type": item.value_type,
        "description": item.description,
    }


async def list_settings(
    session: AsyncSession,
    *,
    params: PageParams,
    q: str | None,
    value_type: str | None,
) -> Page[schemas.SettingOut]:
    rows, total = await SettingsRepository(session).list_items(
        q=q,
        value_type=value_type,
        offset=params.offset,
        limit=params.limit,
    )
    items = [schemas.SettingOut.model_validate(row) for row in rows]
    return Page[schemas.SettingOut].build(items, total=total, params=params)


async def get_setting(session: AsyncSession, key: str) -> schemas.SettingOut:
    item = await SettingsRepository(session).get_by_key(key)
    if item is None:
        raise NotFoundError("Configuracion no encontrada.")
    return schemas.SettingOut.model_validate(item)


async def upsert_setting(
    request: Request,
    session: AsyncSession,
    actor: User,
    key: str,
    body: schemas.SettingUpsert,
) -> schemas.SettingOut:
    normalized_key = ensure_setting_key(key)
    validate_setting_value(normalized_key, body.value, body.value_type)
    description = body.description.strip()
    if not description:
        raise InvalidParameterError("La descripcion no puede estar vacia.")

    repo = SettingsRepository(session)
    item = await repo.get_by_key_for_update(normalized_key)
    if item is None:
        item = SystemSetting(
            key=normalized_key,
            value=body.value,
            value_type=body.value_type,
            description=description,
            updated_by=actor.id,
        )
        session.add(item)
        action = "syste_setting.created"
        before = None
        try:
            await session.flush()
        except IntegrityError as exc:
            await session.rollback()
            raise ConflictError("La configuracion ya existe; recargue e reintente.") from exc
    else:
        if item.value_type != body.value_type:
            raise ConflictError("No se puede cambiar el tipo de una configuracion existente.")
        before = _snapshot(item)
        item.value = body.value
        item.description = description
        item.updated_by = actor.id
        action = "system_setting.updated"
        await session.flush()

    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action=action,
        entity_type="system_setting",
        entity_id=item.id,
        before=before,
        after=_snapshot(item),
    )
    await session.commit()
    await session.refresh(item)
    return schemas.SettingOut.model_validate(item)
