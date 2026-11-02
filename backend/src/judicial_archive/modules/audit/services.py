from __future__ import annotations

import ipaddress
from typing import Any
from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.core.enums import AuditActorType, AuditResult, AuditSource
from judicial_archive.modules.audit.models import AuditEvent
from judicial_archive.modules.users.models import User


def _client_ip(request: Request | None) -> str | None:
    if request is None or request.client is None:
        return None
    raw = request.client.host
    try:
        return str(ipaddress.ip_address(raw))
    except ValueError:
        return None


def _request_id(request: Request | None) -> str | None:
    if request is None:
        return None
    value = getattr(request.state, "request_id", None)
    return value if isinstance(value, str) else None


async def record_audit_event(
    session: AsyncSession,
    *,
    request: Request | None,
    actor: User | None,
    action: str,
    entity_type: str,
    entity_id: UUID | None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    result: AuditResult = AuditResult.SUCCESS,
    source: AuditSource = AuditSource.API,
) -> AuditEvent:
    user_agent = None
    if request is not None:
        user_agent = (request.headers.get("user-agent") or "").strip()[:512] or None

    event = AuditEvent(
        actor_type=AuditActorType.USER.value if actor else AuditActorType.SYSTEM.value,
        actor_user_id=actor.id if actor else None,
        actor_label=actor.username if actor else None,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before_data=before,
        after_data=after,
        metadata_json=metadata,
        request_id=_request_id(request),
        ip_address=_client_ip(request),
        user_agent=user_agent,
        source=source.value,
        result=result.value,
    )
    session.add(event)
    await session.flush()
    return event
