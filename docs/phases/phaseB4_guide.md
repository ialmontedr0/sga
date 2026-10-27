# Fase B4 --- Autenticación, autorización y administración de usuarios

**Versión:** 1.0
**Estado:** guía de implementación (sin código aplicado)
**Fecha:** 2026-10-27
**Ámbito:** backend
**Entrada:** B0-B3 cerradas y verificadas (B3 commiteado `e53e6c3`, B2 commiteado `7d6aa4f`)
**Salida:** autenticación con sesiones opacas en PostgreSQL, protección CSRF, RBAC por roles/permisos, alta segura de administradores, auditoría de seguridad sin secretos, endpoints auth/users/roles/permissions, documentación actualizada

---

## 0. Cómo usar este documento

### 0.1 Regla de alcance

Este documento es una guía de implementación. **No autoriza por sí mismo** a modificar código, ejecutar migraciones sobre bases compartidas, hacer commit ni hacer push. La implementación se realiza únicamente cuando el usuario lo autorice explícitamente.

Toda decisión de B4 debe respetar:

1. `docs/AGENTS.md`
2. `docs/phases/GUIA_DESARROLLO_FASES_SGA.md`, fase B4
3. `docs/phases/phaseB0_guide.md`, `docs/phases/phaseB1_guide.md`, `docs/phases/phaseB2_guide.md`, `docs/phases/phaseB3_guide.md`
4. Estado real: B3 cerrado (`e53e6c3`), B2 cerrado (`7d6aa4f`). `pwdlib[argon2]` ya presente en `backend/pyproject.toml`. Windows requiere `--loop judicial_archive.core.runtime:selector_loop_factory`.

Si alguna instrucción contradice una regla de seguridad o de negocio, prevalece la más restrictiva.

### 0.2 Qué significa "sin omisiones" en B4

Esta guía incluye:

- Árbol exacto de archivos a **crear** y a **modificar**
- Código completo (modelos SQLAlchemy, esquemas Pydantic, repositorios, servicios, routers, dependencias)
- Migración Alembic completa con tablas, índices parciales, constraints, FKs
- Extensión de `core/config.py` con todas las variables de auth/cookies/CSRF/bloqueo
- Extensión completa de `core/security.py`
- Extensión completa de `api/deps.py` con autenticación y autorización RBAC
- Módulos `modules/auth/` y `modules/users/` completos
- Script interactivo `backend/scripts/create_admin.py` sin contraseñas por defecto
- Integración con `api/v1/router.py` y `main.py` si aplica
- Auditoría de seguridad sin guardar secretos/tokens/contraseñas
- Matriz RBAC ejecutable
- Pruebas unitarias, API e integración completas
- Actualización de `docs/api.md`, `docs/roles-y-permisos.md`, `docs/seguridad.md`, `docs/pruebas.md`
- Comandos PowerShell paso a paso
- Checklist de aceptación verificable
- Riesgos, mitigaciones e incertidumbres

**Fuera de alcance:** OAuth/OIDC, 2FA/MFA, recuperación de contraseña por email, rate limiting genérico, frontend.

### 0.3 Principios obligatorios

- **Sesiones opacas**: token aleatorio de alta entropía, solo hash en BD (`auth_sessions.token_hash`)
- **Cookies seguras**: `HttpOnly`, `Secure` (true en producción), `SameSite` configurable, `Path` correcto
- **CSRF**: protección para métodos no idempotentes (POST/PUT/PATCH/DELETE). Comparación en tiempo constante
- **Contraseñas**: `pwdlib.PasswordHash.recommended()` (Argon2id). Nunca almacenar en texto plano
- **RBAC**: `users` ↔ `user_roles` ↔ `roles` ↔ `role_permissions` ↔ `permissions`. Verificar por permiso en servidor
- **Mínimo privilegio**: denegar por defecto
- **Bloqueo por intentos**: `login_attempts` + `users.failed_login_count`. Bloquear temporalmente tras umbral
- **Revocación**: logout, logout-all, revocación por administrador
- **Auditoría**: `security_events` sin secretos, tokens, hashes de sesión, contraseñas
- **Alta segura**: **ÚNICAMENTE** mediante `backend/scripts/create_admin.py`. **PROHIBIDO** semillas/fixtures con contraseñas
- **Sin información sensible en errores**: mensajes genéricos para login fallido

---

## 1. Objetivo, alcance y entregables

### 1.1 Objetivo

Implementar la capa de autenticación, autorización y administración de usuarios para asegurar el acceso al sistema con sesiones opacas, RBAC granular y auditoría completa.

### 1.2 Entregables

| Entregable | Ubicación | Acción |
|---|---|---|
| Configuración auth | `backend/src/judicial_archive/core/config.py` | MODIFICAR |
| Seguridad | `backend/src/judicial_archive/core/security.py` | MODIFICAR/EXTENDER |
| Dependencias authz | `backend/src/judicial_archive/api/deps.py` | MODIFICAR |
| Router v1 | `backend/src/judicial_archive/api/v1/router.py` | MODIFICAR |
| Modelos auth | `backend/src/judicial_archive/modules/auth/models.py` | CREAR/MODIFICAR |
| Módulo auth completo | `backend/src/judicial_archive/modules/auth/*` | CREAR |
| Modelos users/roles/perm | `backend/src/judicial_archive/modules/users/models.py` | MODIFICAR/COMPLETAR |
| Módulo users completo | `backend/src/judicial_archive/modules/users/*` | CREAR/MODIFICAR |
| Migración | `backend/alembic/versions/YYYYMMDD_HHMM_auth_rbac_sessions_security.py` | CREAR |
| Script alta segura | `backend/scripts/create_admin.py` | CREAR |
| Tests | `backend/tests/unit/`, `backend/tests/api/`, `backend/tests/integration/` | CREAR/MODIFICAR |
| Docs | `docs/api.md`, `docs/roles-y-permisos.md`, `docs/seguridad.md`, `docs/pruebas.md` | MODIFICAR/CREAR |

---

## 2. Prerrequisitos y verificación inicial

### 2.1 Verificación
```powershell
Set-Location C:\Users\Tony\Documents\sga
git status --short
git log --oneline -3

Set-Location backend
uv sync
uv run python -c "import pwdlib; from pwdlib import PasswordHash; print('pwdlib ok')"
uv run python -c "import fastapi, pydantic, sqlalchemy, alembic; print('deps ok')"
```

### 2.2 Base de datos
Asegurar `sga_dev` y `sga_test` accesibles. Usar variables de entorno, nunca escribir credenciales en archivos.

```powershell
$env:SGA_DATABASE_URL = "postgresql+psycopg://USER:PASS@localhost:5432/sga_dev"
uv run alembic current
```

---

## 3. Extensión de configuración

### 3.1 Modificar `backend/src/judicial_archive/core/config.py`

Añadir imports y campos al final de `Settings` (antes de validadores):

```python
# Añadir tras readiness_timeout_seconds
    # Autenticación y sesiones (B4)
    auth_session_cookie_name: str = "sga_session"
    auth_session_cookie_secure: bool = True
    auth_session_cookie_httponly: bool = True
    auth_session_cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    auth_session_cookie_path: str = "/"
    auth_session_idle_minutes: int = Field(default=30, ge=5, le=1440)
    auth_session_absolute_hours: int = Field(default=48, ge=1, le=720)
    auth_session_max_age_seconds: int = Field(default=172800, ge=300, le=2592000)

    # CSRF
    auth_csrf_cookie_name: str = "sga_csrf"
    auth_csrf_header_name: str = "X-CSRF-Token"
    auth_csrf_cookie_secure: bool = True
    auth_csrf_cookie_httponly: bool = False
    auth_csrf_cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    auth_csrf_cookie_path: str = "/"
    auth_csrf_max_age_seconds: int = Field(default=172800, ge=300, le=2592000)

    # Login protection
    auth_login_max_attempts: int = Field(default=5, ge=1, le=20)
    auth_login_lockout_minutes: int = Field(default=15, ge=1, le=1440)
    auth_login_window_minutes: int = Field(default=15, ge=1, le=60)

    # Password policy
    auth_password_min_length: int = Field(default=12, ge=8, le=128)
```

Añadir validadores:

```python
@field_validator("auth_session_cookie_samesite", "auth_csrf_cookie_samesite")
@classmethod
def _validate_samesite(cls, v: str) -> str:
    if v.lower() not in {"lax", "strict", "none"}:
        raise ValueError("SameSite debe ser lax|strict|none")
    return v.lower()


@model_validator(mode="after")
def _validate_auth_production(self) -> Self:
    if self.environment is not Environment.PRODUCTION:
        return self
    problems: list[str] = []
    if not self.auth_session_cookie_secure:
        problems.append("auth_session_cookie_secure debe ser true en produccion")
    if not self.auth_csrf_cookie_secure:
        problems.append("auth_csrf_cookie_secure debe ser true en produccion")
    if (
        self.auth_session_cookie_samesite == "none"
        and not self.auth_session_cookie_secure
    ):
        problems.append("SameSite=None requiere Secure=true")
    if self.auth_csrf_cookie_samesite == "none" and not self.auth_csrf_cookie_secure:
        problems.append("SameSite=None requiere Secure=true")
    if problems:
        raise ValueError(
            "Configuracion auth de produccion invalida: " + "; ".join(problems)
        )
    return self
```

Añadir `Literal` a imports si no está.

### 3.2 Actualizar `backend/.env.example`

Añadir sección completa de auth al final:
```dotenv
# === B4: Autenticación, sesiones, CSRF, bloqueo ===
SGA_AUTH_SESSION_COOKIE_NAME=sga_session
SGA_AUTH_SESSION_COOKIE_SECURE=false
SGA_AUTH_SESSION_COOKIE_HTTPONLY=true
SGA_AUTH_SESSION_COOKIE_SAMESITE=lax
SGA_AUTH_SESSION_COOKIE_PATH=/
SGA_AUTH_SESSION_IDLE_MINUTES=30
SGA_AUTH_SESSION_ABSOLUTE_HOURS=48
SGA_AUTH_SESSION_MAX_AGE_SECONDS=172800

SGA_AUTH_CSRF_COOKIE_NAME=sga_csrf
SGA_AUTH_CSRF_HEADER_NAME=X-CSRF-Token
SGA_AUTH_CSRF_COOKIE_SECURE=false
SGA_AUTH_CSRF_COOKIE_HTTPONLY=false
SGA_AUTH_CSRF_COOKIE_SAMESITE=lax
SGA_AUTH_CSRF_COOKIE_PATH=/
SGA_AUTH_CSRF_MAX_AGE_SECONDS=172800

SGA_AUTH_LOGIN_MAX_ATTEMPTS=5
SGA_AUTH_LOGIN_LOCKOUT_MINUTES=15
SGA_AUTH_LOGIN_WINDOW_MINUTES=15

SGA_AUTH_PASSWORD_MIN_LENGTH=12
```

---

## 4. Extensión de seguridad

### 4.1 Reemplazar/Extender `backend/src/judicial_archive/core/security.py`

Código completo:

```python
from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from pwdlib import PasswordHash

_MIN_TOKEN_BYTES = 32
_MAX_PASSWORD_LENGTH = 1024
_SESSION_TOKEN_BYTES = 48
_CSRF_TOKEN_BYTES = 32

_hasher = PasswordHash.recommended()

logger = structlog.get_logger(__name__)


def hash_password(password: str) -> str:
    if not password:
        raise ValueError("La contrasena no puede estar vacia.")
    if len(password) > _MAX_PASSWORD_LENGTH:
        raise ValueError(
            f"La contrasena supera el maximo de {_MAX_PASSWORD_LENGTH} caracteres."
        )
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    if not password or not password_hash:
        return False
    if len(password) > _MAX_PASSWORD_LENGTH:
        return False
    try:
        return _hasher.verify(password, password_hash)
    except Exception as exc:
        logger.warning("password_verification_failed", error_type=type(exc).__name__)
        return False


def generate_opaque_token(nbytes: int = _MIN_TOKEN_BYTES) -> str:
    if nbytes < _MIN_TOKEN_BYTES:
        raise ValueError(
            f"El token debe tener al menos {_MIN_TOKEN_BYTES} bytes de entropia."
        )
    return secrets.token_urlsafe(nbytes)


def generate_session_token() -> str:
    return secrets.token_urlsafe(_SESSION_TOKEN_BYTES)


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(_CSRF_TOKEN_BYTES)


def hash_opaque_token(token: str) -> str:
    if not token:
        raise ValueError("El token no puede estar vacio.")
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def verify_opaque_token(token: str, token_hash: str) -> bool:
    if not token or not token_hash:
        return False
    try:
        return hmac.compare_digest(hash_opaque_token(token), token_hash)
    except Exception:
        return False


def constant_time_compare(a: str, b: str) -> bool:
    if not isinstance(a, str) or not isinstance(b, str):
        return False
    try:
        return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))
    except Exception:
        return False


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def compute_session_expiry(
    idle_minutes: int, absolute_hours: int
) -> tuple[datetime, datetime]:
    now = now_utc()
    expires_at = now + timedelta(minutes=idle_minutes)
    absolute_expires_at = now + timedelta(hours=absolute_hours)
    if absolute_expires_at < expires_at:
        absolute_expires_at = expires_at
    return expires_at, absolute_expires_at


def is_expired(dt: datetime | None) -> bool:
    if dt is None:
        return True
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt < now_utc()
```

---

## 5. Modelos

### 5.1 Completar `backend/src/judicial_archive/modules/users/models.py`

Reemplazar/completar con código completo (mantener estilo B2):

```python
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
    text,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from judicial_archive.core.enums import CatalogStatus, UserStatus
from judicial_archive.db.base import Base
from judicial_archive.db.mixins import (
    OptimisticLockMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    check_in,
)


class Role(UUIDPrimaryKeyMixin, TimestampMixin, OptimisticLockMixin, Base):
    __tablename__ = "roles"
    __table_args__ = (
        check_in("status", CatalogStatus, name="ck_roles_status"),
        CheckConstraint("code ~ '^[A-Z][A-Z0-9_]{1,63}$'", name="ck_roles_code_format"),
        CheckConstraint("length(btrim(name)) > 0", name="ck_roles_name_not_empty"),
    )

    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_system: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=CatalogStatus.ACTIVE.value,
        server_default=CatalogStatus.ACTIVE.value,
    )


class Permission(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "permissions"
    __table_args__ = (
        CheckConstraint(
            "code ~ '^[a-z][a-z0-9_]*(\\.[a-z][a-z0-9_]*)+$'",
            name="ck_permissions_code_format",
        ),
        CheckConstraint(
            "length(btrim(name)) > 0", name="ck_permissions_name_not_empty"
        ),
    )

    code: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)


class User(UUIDPrimaryKeyMixin, TimestampMixin, OptimisticLockMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        check_in("status", UserStatus, name="ck_users_status"),
        CheckConstraint(
            "username_normalized = lower(btrim(username))",
            name="ck_users_username_normalized",
        ),
        CheckConstraint(
            "email IS NULL OR email_normalized = lower(btrim(email))",
            name="ck_users_email_normalized",
        ),
        CheckConstraint(
            "(email IS NULL AND email_normalized IS NULL) OR (email IS NOT NULL AND email_normalized IS NOT NULL)",
            name="ck_users_email_pair",
        ),
        CheckConstraint(
            "length(password_hash) >= 20", name="ck_users_password_hash_not_empty"
        ),
        Index("ix_users_status", "status"),
        Index("ix_users_display_name", "display_name"),
    )

    username: Mapped[str] = mapped_column(String(64), nullable=False)
    username_normalized: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True
    )
    email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    email_normalized: Mapped[str | None] = mapped_column(
        String(254), nullable=True, unique=True
    )
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    password_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    must_change_password: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=UserStatus.ACTIVE.value,
        server_default=UserStatus.ACTIVE.value,
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    failed_login_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class UserRole(Base):
    __tablename__ = "user_roles"
    __table_args__ = (Index("ix_user_roles_role_id", "role_id"),)

    user_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    role_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    assigned_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )


class RolePermission(Base):
    __tablename__ = "role_permissions"
    __table_args__ = (Index("ix_role_permissions_permission_id", "permission_id"),)

    role_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    permission_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    granted_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
```

### 5.2 Crear/modificar `backend/src/judicial_archive/modules/auth/models.py`

```python
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
    text,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from judicial_archive.db.base import Base
from judicial_archive.db.mixins import UUIDPrimaryKeyMixin


class AuthSession(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "auth_sessions"
    __table_args__ = (
        CheckConstraint(
            "length(token_hash) = 64", name="ck_auth_sessions_token_hash_len"
        ),
        CheckConstraint(
            "expires_at > created_at", name="ck_auth_sessions_expires_after_created"
        ),
        CheckConstraint(
            "absolute_expires_at >= expires_at",
            name="ck_auth_sessions_absolute_ge_expires",
        ),
        CheckConstraint(
            "revoked_at IS NULL OR revoked_at >= created_at",
            name="ck_auth_sessions_revoked_after_created",
        ),
        Index("ix_auth_sessions_user_id", "user_id"),
        Index("ix_auth_sessions_expires_at", "expires_at"),
        Index("ix_auth_sessions_token_hash", "token_hash", unique=True),
        Index(
            "ix_auth_sessions_active_user",
            "user_id",
            postgresql_where=text("revoked_at IS NULL"),
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    csrf_token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    absolute_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    revocation_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)


class LoginAttempt(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "login_attempts"
    __table_args__ = (
        Index("ix_login_attempts_username_at", "username", "attempted_at"),
        Index("ix_login_attempts_ip_at", "ip_address", "attempted_at"),
    )

    username: Mapped[str] = mapped_column(String(64), nullable=False)
    username_normalized: Mapped[str] = mapped_column(String(64), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(50), nullable=True)
    attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class SecurityEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "security_events"
    __table_args__ = (
        Index("ix_security_events_type_at", "event_type", "occurred_at"),
        Index("ix_security_events_user_at", "user_id", "occurred_at"),
        Index("ix_security_events_actor_at", "actor_id", "occurred_at"),
    )

    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    user_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    actor_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
```

Añadir `__init__.py` en `modules/auth/` si no existe.

---

## 6. Migración Alembic

### 6.1 Generar
```powershell
cd backend
uv run alembic revision --autogenerate -m "auth_rbac_sessions_security"
```

### 6.2 Revisar migración

Debe incluir:
- Crear/alter `users` (añadir `locked_until` si falta)
- Crear `roles`, `permissions`, `user_roles`, `role_permissions`
- Crear `auth_sessions`, `login_attempts`, `security_events`
- Índices parciales
- Checks
- FKs con `ON DELETE` correcto
- Sin `DROP` destructivo

### 6.3 Aplicar
```powershell
uv run alembic upgrade head
uv run alembic check
```

---

## 7. Dependencias de autenticación y autorización

### 7.1 Extender `backend/src/judicial_archive/api/deps.py`

Reemplazar/extender con código completo:

```python
from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any, cast
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.core.config import Settings
from judicial_archive.core.enums import UserStatus
from judicial_archive.core.security import hash_opaque_token, is_expired
from judicial_archive.db.session import Database
from judicial_archive.modules.auth.models import AuthSession
from judicial_archive.modules.users.models import (
    Permission,
    Role,
    RolePermission,
    User,
    UserRole,
)


def get_app_settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


def get_database(request: Request) -> Database:
    return cast(Database, request.app.state.database)


def get_redis(request: Request) -> Redis:
    return cast(Redis, request.app.state.redis)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    database = get_database(request)
    async with database.session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_app_settings),
) -> User:
    cookie_name = settings.auth_session_cookie_name
    token = request.cookies.get(cookie_name)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado"
        )

    token_hash = hash_opaque_token(token)
    now = datetime.now(timezone.utc)

    result = await session.execute(
        select(AuthSession).where(AuthSession.token_hash == token_hash)
    )
    auth_session = result.scalar_one_or_none()

    if not auth_session or auth_session.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesión inválida"
        )

    if is_expired(auth_session.expires_at) or is_expired(
        auth_session.absolute_expires_at
    ):
        auth_session.revoked_at = now
        auth_session.revocation_reason = "expired"
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesión expirada"
        )

    result = await session.execute(select(User).where(User.id == auth_session.user_id))
    user = result.scalar_one_or_none()

    if not user or user.status != UserStatus.ACTIVE.value:
        auth_session.revoked_at = now
        auth_session.revocation_reason = "user_inactive"
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no autorizado"
        )

    if user.locked_until and user.locked_until > now:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Cuenta bloqueada"
        )

    # actualizar last_seen_at
    auth_session.last_seen_at = now
    user.last_login_at = user.last_login_at or now
    await session.commit()
    await session.refresh(user)

    request.state.current_user = user
    request.state.auth_session_id = auth_session.id
    return user


async def get_current_user_optional(
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_app_settings),
) -> User | None:
    try:
        return await get_current_user(request, session, settings)
    except HTTPException:
        return None


def require_permissions(*required: str):
    async def dependency(
        current_user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_session),
    ) -> User:
        if not required:
            return current_user

        # Obtener permisos del usuario (directos no hay, via roles)
        stmt = (
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(Role, Role.id == RolePermission.role_id)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == current_user.id)
            .where(Role.status == "ACTIVE")
        )
        result = await session.execute(stmt)
        user_perms = {row[0] for row in result.all()}

        # Admin bypass opcional: si tiene rol Administrador con todos permisos, permitir
        # pero mejor verificar explícitamente
        for p in required:
            if p not in user_perms:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Permisos insuficientes",
                )
        return current_user

    return dependency


def require_roles(*required: str):
    async def dependency(
        current_user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_session),
    ) -> User:
        if not required:
            return current_user
        stmt = (
            select(Role.code)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == current_user.id)
            .where(Role.status == "ACTIVE")
        )
        result = await session.execute(stmt)
        user_roles = {row[0] for row in result.all()}
        for r in required:
            if r not in user_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail="Rol insuficiente"
                )
        return current_user

    return dependency
```

---

## 8. Módulo Auth

### 8.1 Estructura
```text
backend/src/judicial_archive/modules/auth/
├── __init__.py
├── models.py
├── schemas.py
├── repositories.py
├── services.py
├── routers.py
├── dependencies.py
└── permissions.py
```

### 8.2 `schemas.py`
```python
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=1, max_length=1024)
    csrf_token: str | None = None


class UserMe(BaseModel):
    id: UUID
    username: str
    email: str | None
    display_name: str
    status: str
    must_change_password: bool
    roles: list[str] = []
    permissions: list[str] = []

    class Config:
        from_attributes = True


class SessionInfo(BaseModel):
    id: UUID
    created_at: datetime
    last_seen_at: datetime | None
    expires_at: datetime
    ip_address: str | None
    user_agent: str | None


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=1024)
    new_password: str = Field(min_length=12, max_length=1024)
    csrf_token: str | None = None


class MessageResponse(BaseModel):
    message: str
```

### 8.3 `repositories.py`
```python
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.modules.auth.models import (
    AuthSession,
    LoginAttempt,
    SecurityEvent,
)
from judicial_archive.modules.users.models import User


class AuthRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_user_by_username(self, username: str) -> User | None:
        res = await self.session.execute(
            select(User).where(User.username_normalized == username.lower().strip())
        )
        return res.scalar_one_or_none()

    async def count_recent_failed(
        self, username_normalized: str, since: datetime
    ) -> int:
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

    async def revoke_session(
        self, session_id: UUID, revoked_by: UUID | None, reason: str
    ) -> None:
        await self.session.execute(
            update(AuthSession)
            .where(AuthSession.id == session_id)
            .values(
                revoked_at=datetime.now(timezone.utc),
                revoked_by=revoked_by,
                revocation_reason=reason,
            )
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
                revoked_at=datetime.now(timezone.utc),
                revoked_by=revoked_by,
                revocation_reason=reason,
            )
        )

    async def log_security_event(self, event: SecurityEvent) -> None:
        self.session.add(event)
```

### 8.4 `services.py` (lógica crítica)
Implementar:
- `login()`: verificar usuario, verificar estado/bloqueo, contar intentos fallidos recientes, verificar contraseña, actualizar `failed_login_count`/`locked_until`, crear sesión + cookies CSRF, registrar eventos, commit
- `logout()`: revocar sesión actual
- `logout_all()`: revocar todas
- `change_password()`: validar actual, política mínima, hashear nueva, revocar otras sesiones, actualizar flags
- `get_me()`: cargar roles/permisos

**Reglas:** nunca revelar si usuario existe o no en mensaje de error. Usar "Credenciales inválidas".

### 8.5 `routers.py`
```python
from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.api.deps import get_current_user, get_session
from judicial_archive.core.config import Settings, get_app_settings
from judicial_archive.modules.auth import schemas, services
from judicial_archive.modules.users.models import User

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/login", response_model=schemas.MessageResponse)
async def login(
    request: Request,
    body: schemas.LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_app_settings),
):
    return await services.login(request, response, session, settings, body)


@router.post("/logout", response_model=schemas.MessageResponse)
async def logout(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_app_settings),
):
    return await services.logout(request, response, session, settings, current_user)


@router.post("/logout-all", response_model=schemas.MessageResponse)
async def logout_all(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_app_settings),
):
    return await services.logout_all(request, response, session, settings, current_user)


@router.get("/me", response_model=schemas.UserMe)
async def me(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await services.get_me(session, current_user)


@router.post("/change-password", response_model=schemas.MessageResponse)
async def change_password(
    request: Request,
    response: Response,
    body: schemas.ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_app_settings),
):
    return await services.change_password(
        request, response, session, settings, current_user, body
    )
```

### 8.6 Integrar router
Modificar `backend/src/judicial_archive/api/v1/router.py`:
```python
from judicial_archive.modules.auth.routers import router as auth_router

api_router.include_router(auth_router)
```

---

## 9. Módulo Users (admin)

### 9.1 Estructura
```text
backend/src/judicial_archive/modules/users/
├── __init__.py
├── schemas.py
├── repositories.py
├── services.py
├── routers.py
└── permissions.py
```

### 9.2 `permissions.py`
```python
USERS_READ = "users.read"
USERS_CREATE = "users.create"
USERS_UPDATE = "users.update"
USERS_DELETE = "users.delete"
USERS_LOCK = "users.lock"
ROLES_MANAGE = "roles.manage"
PERMISSIONS_MANAGE = "permissions.manage"
SESSIONS_MANAGE = "sessions.manage"
```

### 9.3 Endpoints (con `require_permissions`)
- `GET /api/v1/users/` - listar
- `POST /api/v1/users/` - crear
- `GET /api/v1/users/{id}` - detalle
- `PATCH /api/v1/users/{id}` - actualizar
- `POST /api/v1/users/{id}/lock` - bloquear/desbloquear
- `POST /api/v1/users/{id}/reset-password` - forzar cambio contraseña
- `GET /api/v1/roles/`, `POST /api/v1/roles/`, `POST /api/v1/roles/{id}/permissions`
- `GET /api/v1/permissions/`

Proteger con `Depends(require_permissions(...))`. Registrar `security_events` en cambios sensibles.

---

## 10. Script de alta segura de administradores

### 10.1 Crear `backend/scripts/create_admin.py`

```python
#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import getpass
import sys
from pathlib import Path

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from judicial_archive.core.config import get_settings
from judicial_archive.core.enums import UserStatus
from judicial_archive.core.security import hash_password
from judicial_archive.modules.auth.models import SecurityEvent
from judicial_archive.modules.users.models import Role, User, UserRole


async def main() -> None:
    print("=== ALTA SEGURA DE ADMINISTRADOR - SGA ===")
    print("Este script NO usa contraseñas por defecto.")
    print()

    username = input("Usuario (3-64): ").strip()
    if len(username) < 3:
        print("Usuario inválido")
        sys.exit(1)
    email = input("Email (opcional): ").strip() or None
    display_name = input("Nombre completo: ").strip()
    if not display_name:
        print("Nombre requerido")
        sys.exit(1)

    while True:
        pwd1 = getpass.getpass("Contraseña (mínimo 12): ")
        if len(pwd1) < 12:
            print("Mínimo 12 caracteres")
            continue
        pwd2 = getpass.getpass("Confirmar contraseña: ")
        if pwd1 != pwd2:
            print("No coinciden")
            continue
        break

    settings = get_settings()
    engine = create_async_engine(str(settings.database_url))
    SessionLocal = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with SessionLocal() as session:
        async with session.begin():
            res = await session.execute(
                select(User).where(User.username_normalized == username.lower())
            )
            if res.scalar_one_or_none():
                print("Usuario ya existe")
                sys.exit(1)

            res = await session.execute(
                select(Role).where(Role.code == "ADMINISTRADOR")
            )
            role = res.scalar_one_or_none()
            if not role:
                print(
                    "Rol ADMINISTRADOR no existe. Ejecutar migración/semillas base primero."
                )
                sys.exit(1)

            user = User(
                username=username,
                username_normalized=username.lower(),
                email=email,
                email_normalized=email.lower() if email else None,
                display_name=display_name,
                password_hash=hash_password(pwd1),
                status=UserStatus.ACTIVE.value,
                must_change_password=False,
                failed_login_count=0,
            )
            session.add(user)
            await session.flush()

            session.add(UserRole(user_id=user.id, role_id=role.id))
            session.add(
                SecurityEvent(
                    event_type="admin_created_via_script",
                    user_id=user.id,
                    details={"username": username},
                )
            )

        print(f"Administrador creado: {username} ({user.id})")
        print("Recuerde: no compartir credenciales. Usar mínimo privilegio.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
```

Crear directorio `backend/scripts/` si no existe.

**USO:**
```powershell
cd backend
uv run python scripts/create_admin.py
```

**NUNCA** commitear contraseñas. **NUNCA** crear usuarios admin por migración con contraseñas.

---

## 11. Pruebas

### 11.1 Unitarias
Crear:
- `backend/tests/unit/test_auth_security.py` - hash_password/verify, tokens, CSRF
- `backend/tests/unit/test_auth_config.py` - validaciones auth

### 11.2 API
Crear:
- `backend/tests/api/test_auth_login.py` - login exitoso/fallido, bloqueo
- `backend/tests/api/test_auth_session.py` - me/logout/logout-all
- `backend/tests/api/test_auth_csrf.py` - protección CSRF
- `backend/tests/api/test_users_rbac.py` - permisos

### 11.3 Integración
Crear/actualizar en `backend/tests/integration/`:
- `test_auth_flow_integration.py` - flujo completo
- Verificar skip si faltan variables

Ejecutar:
```powershell
cd backend
uv run pytest tests/unit/test_auth_security.py -v
uv run pytest tests/api/test_auth_login.py -v
uv run pytest -q
```

---

## 12. Actualización de documentación

### 12.1 `docs/api.md`
Añadir sección "Autenticación (B4)" con endpoints, cookies, CSRF, ejemplos.

### 12.2 `docs/roles-y-permisos.md`
Crear/actualizar con roles iniciales: `Administrador`, `Supervisor de archivo`, `Archivista`, `Digitalizador`, `Consulta` y permisos por módulo.

### 12.3 `docs/seguridad.md`
Añadir: sesiones opacas, HttpOnly/Secure/SameSite, CSRF, bloqueo por intentos, revocación, auditoría sin secretos, alta segura.

### 12.4 `docs/pruebas.md`
Añadir sección pruebas B4.

---

## 13. Comandos de validación completos

```powershell
# Setup
cd C:\Users\Tony\Documents\sga\backend
uv sync

# Migración
uv run alembic revision --autogenerate -m "auth_rbac_sessions_security"
# Revisar migración manualmente
uv run alembic upgrade head
uv run alembic check

# Calidad
uv run ruff check .
uv run ruff format --check .
uv run mypy src tests

# Tests
uv run pytest -q
uv run pytest --cov=judicial_archive --cov-report=term-missing

# Crear primer admin (interactivo)
uv run python scripts/create_admin.py

# Ejecutar
uv run uvicorn judicial_archive.asgi:app --reload --host 127.0.0.1 --port 8000 --loop judicial_archive.core.runtime:selector_loop_factory
```

---

## 14. Checklist de aceptación B4

### Configuración y seguridad
- [ ] `core/config.py` extendido con auth/cookies/CSRF/bloqueo
- [ ] `core/security.py` extendido con tokens/sesiones/CSRF
- [ ] Validaciones producción correctas
- [ ] `.env.example` actualizado

### Base de datos
- [ ] Migración generada y revisada manualmente
- [ ] Tablas `users`,`roles`,`permissions`,`user_roles`,`role_permissions`,`auth_sessions`,`login_attempts`,`security_events` creadas
- [ ] Índices parciales correctos
- [ ] `alembic upgrade head` exitoso
- [ ] `alembic check` sin diferencias

### Autenticación/Autorización
- [ ] `api/deps.py` con `get_current_user`, `require_permissions`, `require_roles`
- [ ] Módulo `auth/` completo
- [ ] Módulo `users/` completo con CRUD protegido
- [ ] Router integrado en `api/v1`
- [ ] Cookies HttpOnly/Secure/SameSite configuradas
- [ ] CSRF aplicado a métodos no idempotentes
- [ ] Bloqueo por intentos implementado
- [ ] Revocación de sesiones funcional

### Alta segura y auditoría
- [ ] `scripts/create_admin.py` interactivo sin contraseñas por defecto
- [ ] `security_events` registra eventos sin secretos
- [ ] Sin contraseñas en logs/código/semillas

### Pruebas y calidad
- [ ] Tests unitarios/auth pasan
- [ ] Tests API auth/rbac pasan
- [ ] Tests integración pasan (con variables)
- [ ] `ruff check` OK
- [ ] `ruff format --check` OK
- [ ] `mypy` OK
- [ ] Cobertura >= umbral proyecto

### Documentación
- [ ] `docs/api.md` actualizado
- [ ] `docs/roles-y-permisos.md` creado/actualizado
- [ ] `docs/seguridad.md` actualizado
- [ ] `docs/pruebas.md` actualizado

---

## 15. Riesgos y mitigaciones

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Fuga de token en logs | Alto | Nunca loggear token/cookie. Usar solo hashes. |
| CSRF bypass | Alto | Aplicar a POST/PUT/PATCH/DELETE. Comparación tiempo constante. |
| Brute force | Alto | Bloqueo por usuario + ventana temporal. Mensajes genéricos. |
| Sesiones huérfanas | Medio | Limpieza por expiración. Índices adecuados. |
| Escalado de privilegios | Alto | Verificación servidor en toda ruta protegida. Roles sistema no borrables. |
| Alta insegura | Alto | Solo script interactivo. Sin semillas con contraseñas. |

---

**NOTA FINAL:** Esta guía es **únicamente documentación**. No se ha ejecutado ningún código, no se han creado migraciones, no se han modificado archivos, no se ha hecho commit. Seguir estrictamente en orden cuando se autorice la implementación.
