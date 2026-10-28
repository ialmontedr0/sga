from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.modules.auth.models import AuthSession, LoginAttempt, SecurityEvent
from judicial_archive.modules.users.models import User


class AuthRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_user_by_username(self, username: str) -> User | None:
        res = await self.session.execute(
            select(User).where(User.username_normalized == username.lower().strip())
        )
        return res.scalar_one_or_none()

    async def count_recent_failed(self, username_normalized: str, since: datetime) -> int:
        res = await self.session.execute(
            select(func.count(LoginAttempt.id)).where(
                LoginAttempt.username_normalized == username_normalized,
                LoginAttempt.success == False,  # noqa: E712
                LoginAttempt.attempted_at >= since,
            )
        )
        return int(res.scalar_one() or 0)

    async def log_attempt(self, attempt: LoginAttempt) -> None:
        self.session.add(attempt)

    async def create_session(self, auth_session: AuthSession) -> AuthSession:
        self.session.add(auth_session)
        await self.session.flush()
        return auth_session

    async def revoke_session(self, session_id: UUID, revoked_by: UUID | None, reason: str) -> None:
        await self.session.execute(
            update(AuthSession)
            .where(AuthSession.id == session_id)
            .values(revoked_at=datetime.now(UTC), revoked_by=revoked_by, revocation_reason=reason)
        )

    async def revoke_all_user_sessions(
        self,
        user_id: UUID,
        revoked_by: UUID | None,
        reason: str,
        except_session_id: UUID | None = None,
    ) -> None:
        stmt = update(AuthSession).where(
            AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None)
        )
        if except_session_id:
            stmt = stmt.where(AuthSession.id != except_session_id)
        await self.session.execute(
            stmt.values(
                revoked_at=datetime.now(UTC), revoked_by=revoked_by, revocation_reason=reason
            )
        )

    async def log_security_event(self, event: SecurityEvent) -> None:
        self.session.add(event)
