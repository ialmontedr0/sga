# Fase B4 --- Autenticación, autorización y administración de usuarios

**Versión:** 1.0
**Estado:** núcleo B4 aplicado en el árbol de trabajo; cierre pendiente (secciones 16-23)
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
uv run mypy src

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

## 16. Estado real y alcance del cierre

### 16.1 Núcleo ya implementado en el árbol de trabajo

La tabla siguiente evita confundir "documentado" con "aplicado". Verificar siempre con `git status --short` antes de continuar.

| Área | Estado real | Evidencia |
|---|---|---|
| Configuración auth/cookies/CSRF | Aplicado | `core/config.py`, `auth_csrf_*`, `auth_session_*`, validaciones de producción |
| Seguridad de contraseñas y tokens | Aplicado | `core/security.py` con Argon2id, SHA-256 y comparación en tiempo constante |
| Modelos RBAC y sesiones | Aplicado | `modules/users/models.py`, `modules/auth/models.py` |
| Migración B4 | Aplicada y verificada | `alembic/versions/88ae4fe9cb05_auth_rbac_sessions_security.py` (`down_revision = 20261026_0001`) |
| Dependencias `get_current_user`/RBAC | Aplicado | `api/deps.py` |
| Login/logout/me/change-password | Aplicado | `modules/auth/{routers,services,repositories,schemas}.py` |
| CRUD de usuarios | Aplicado | `modules/users/{routers,services,repositories}.py` |
| Alta segura de administrador | Aplicado | `scripts/create_admin.py` |
| Suite de pruebas | En verde | `136 passed`, cobertura `82.26 %` |
| Calidad | En verde | `ruff check .`, `ruff format --check .`, `mypy src` |
| Detalle `UserOut.last_login_at` | Corregido | Antes decía `last_lgoin_at` y rompía `GET /users/` |

### 16.2 Brechas que cierra este bloque

| # | Brecha | Consecuencia actual | Solución en este bloque |
|---|---|---|---|
| 1 | `permissions` y `role_permissions` vacías | Todo endpoint con `require_permissions` devuelve `403`, incluso al administrador | Sección 17: seed RBAC idempotente |
| 2 | CSRF emitido pero no validado | Un POST podía ejecutarse sin `X-CSRF-Token` | Sección 18: middleware + endpoint `/auth/csrf` + vínculo con la sesión |
| 3 | Sin endpoints de roles/permisos | No se puede administrar RBAC por API | Sección 19 |
| 4 | Sin detalle de usuario ni reset de contraseña | El administrador no puede operar cuentas por API | Sección 19.6 |
| 5 | Sin listado/revocación de sesiones por administrador | No se puede expulsar una sesión comprometida | Sección 19.7 |
| 6 | Tests RBAC/CSRF ausentes | Regresiones no detectadas | Sección 20 |
| 7 | Documentación B4 incompleta | Operación y auditoría sin referencia | Sección 21 |
| 8 | Roles con permisos desconocidos se ignoraban en silencio | Escalado/degradación silenciosa | Sección 19.5: validación estricta de códigos |

### 16.3 Orden obligatorio de implementación

1. **Seed RBAC** (sección 17). Sin esto, nada protegido por permisos funciona.
2. **Configuración CSRF y middleware** (sección 18).
3. **Cambios en login y `get_current_user`** para vincular CSRF a la sesión (sección 18.5).
4. **Módulo `roles`** y endpoints de permisos (sección 19).
5. **Extensiones de usuarios**: detalle, reset de contraseña, sesiones (secciones 19.6 y 19.7).
6. **Pruebas** (sección 20).
7. **Documentación** (sección 21).
8. **Validación integral** (sección 22) y checklist (sección 22.8).

No invertir el orden: los tests de API necesitan el seed y el CSRF para poder autenticarse.

### 16.4 Criterio de terminado del cierre

- `uv run python -m judicial_archive.db.seed_rbac` deja el catálogo completo y es idempotente.
- Un administrador creado con `scripts/create_admin.py` obtiene `200` en `GET /api/v1/users/`.
- Un usuario con rol `CONSULTA` obtiene `403` en `GET /api/v1/users/`.
- Todo `POST`/`PUT`/`PATCH`/`DELETE` sin `X-CSRF-Token` válido devuelve `403`.
- Existen `GET/POST /api/v1/roles/`, `POST /api/v1/roles/{id}/permissions` y `GET /api/v1/permissions/`.
- Existen `GET /api/v1/users/{id}`, `POST /api/v1/users/{id}/reset-password` y la revocación de sesiones.
- Suite completa en verde y cobertura global `>= 75 %` (objetivo del cierre: `>= 85 %` en módulos nuevos).
- Documentación de la sección 21 publicada.

---

## 17. Seed RBAC: permisos y asociaciones rol-permiso

### 17.1 Dependencias

**No se requieren dependencias nuevas.** Todo se apoya en lo ya instalado:

| Dependencia | Uso en este bloque |
|---|---|
| `sqlalchemy[asyncio]` | Consultas e inserciones idempotentes |
| `pydantic[email]` | `EmailStr` en usuarios (ya instalado) |
| `pwdlib[argon2]` | Hash de contraseñas (ya instalado) |
| `pytest`, `pytest-asyncio`, `pytest-cov` | Pruebas y cobertura |
| PostgreSQL real | Verificación de constraints e idempotencia |
| Redis real | Solo para los tests de integración que levantan la app |

No añadir `flask-seasurf`, `itsdangerous`, `fastapi-csrf-protect` ni similares: el diseño es *double-submit cookie* + vínculo con la sesión y no necesita dependencias externas.

### 17.2 Catálogo de permisos

Reemplazar `backend/src/judicial_archive/modules/users/permissions.py` por:

```python
"""Codigos de permiso del sistema.

Formato obligatorio (CHECK en base de datos):
    ^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$

Los permisos de modulos futuros se declaran aqui desde B4 para que el seed
RBAC sea estable. No implica que sus endpoints existan todavia.
"""

# Usuarios
USERS_READ = "users.read"
USERS_CREATE = "users.create"
USERS_UPDATE = "users.update"
USERS_DELETE = "users.delete"
USERS_LOCK = "users.lock"
USERS_RESET_PASSWORD = "users.reset_password"

# Roles y permisos
ROLES_READ = "roles.read"
ROLES_MANAGE = "roles.manage"
PERMISSIONS_READ = "permissions.read"
PERMISSIONS_MANAGE = "permissions.manage"

# Sesiones y auditoria
SESSIONS_READ = "sessions.read"
SESSIONS_MANAGE = "sessions.manage"
AUDIT_READ = "audit.read"

# Catalogos y busqueda
CATALOG_READ = "catalog.read"
CATALOG_MANAGE = "catalog.manage"
SEARCH_READ = "search.read"

# Cajas y expedientes
BOXES_READ = "boxes.read"
BOXES_CREATE = "boxes.create"
BOXES_UPDATE = "boxes.update"
BOXES_DELETE = "boxes.delete"
CASES_READ = "cases.read"
CASES_CREATE = "cases.create"
CASES_UPDATE = "cases.update"

# Documentos y archivos
DOCUMENTS_READ = "documents.read"
DOCUMENTS_MANAGE = "documents.manage"
FILES_READ = "files.read"
FILES_UPLOAD = "files.upload"
FILES_DOWNLOAD = "files.download"

# Importaciones, OCR y prestamos
IMPORTS_READ = "imports.read"
IMPORTS_CREATE = "imports.create"
IMPORTS_APPROVE = "imports.approve"
OCR_REVIEW = "ocr.review"
LOANS_READ = "loans.read"
LOANS_MANAGE = "loans.manage"
MOVEMENTS_READ = "movements.read"
MOVEMENTS_MANAGE = "movements.manage"
INVENTORY_READ = "inventory.read"
INVENTORY_MANAGE = "inventory.manage"

# Reportes y configuracion
REPORTS_READ = "reports.read"
REPORTS_EXPORT = "reports.export"
SETTINGS_READ = "settings.read"
SETTINGS_MANAGE = "settings.manage"
```

> `users.delete` se reserva para la baja lógica de usuarios. Si no se implementa en B4, el permiso puede existir sin endpoint; lo prohibido es crear endpoints ficticios.

### 17.3 Matriz rol → permiso

Los códigos de rol existentes son `ADMINISTRADOR`, `SUPERVISOR`, `ARCHIVISTA`, `DIGITALIZADOR` y `CONSULTA` (ver `db/seed.py`). La siguiente matriz respeta la matriz funcional de `AGENTS.md` y aplica mínimo privilegio.

| Permiso | ADMINISTRADOR | SUPERVISOR | ARCHIVISTA | DIGITALIZADOR | CONSULTA |
|---|:---:|:---:|:---:|:---:|:---:|
| `users.read` | Sí | Sí | No | No | No |
| `users.create/update/delete/lock/reset_password` | Sí | No | No | No | No |
| `roles.read` / `permissions.read` | Sí | Sí | No | No | No |
| `roles.manage` / `permissions.manage` | Sí | No | No | No | No |
| `sessions.read` | Sí | Sí | No | No | No |
| `sessions.manage` | Sí | Sí | No | No | No |
| `audit.read` | Sí | Sí | No | No | No |
| `catalog.read` | Sí | Sí | Sí | Sí | Sí |
| `catalog.manage` | Sí | Sí | No | No | No |
| `search.read` | Sí | Sí | Sí | Sí | Sí |
| `boxes.read` | Sí | Sí | Sí | Sí | Sí |
| `boxes.create/update` | Sí | Sí | Sí | No | No |
| `boxes.delete` | Sí | No | No | No | No |
| `cases.read` | Sí | Sí | Sí | Sí | Sí |
| `cases.create/update` | Sí | Sí | Sí | No | No |
| `documents.read` | Sí | Sí | Sí | Sí | Sí |
| `documents.manage` | Sí | Sí | Sí | No | No |
| `files.read` / `files.download` | Sí | Sí | Sí | Sí | Sí |
| `files.upload` | Sí | Sí | Sí | Sí | No |
| `imports.read` / `imports.create` | Sí | Sí | Sí | Sí | No |
| `imports.approve` | Sí | Sí | No | No | No |
| `ocr.review` | Sí | Sí | No | Sí | No |
| `loans.read/manage` | Sí | Sí | Sí | No | No |
| `movements.read/manage` | Sí | Sí | Sí | No | No |
| `inventory.read/manage` | Sí | Sí | Sí | No | No |
| `reports.read` | Sí | Sí | Sí | No | Sí |
| `reports.export` | Sí | Sí | No | No | No |
| `settings.read` | Sí | Sí | No | No | No |
| `settings.manage` | Sí | No | No | No | No |

Regla adicional: el rol `ADMINISTRADOR` **no se puede restringir por API**; siempre conserva el catálogo completo. Los permisos nuevos se incorporan ejecutando el seed.

### 17.4 Crear `backend/src/judicial_archive/db/seed_rbac.py`

```python
from __future__ import annotations

import asyncio

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.core.config import get_settings
from judicial_archive.core.enums import CatalogStatus
from judicial_archive.db.session import Database
from judicial_archive.modules.users.models import Permission, Role, RolePermission

SEED_RBAC_LOCK_KEY = 20261027

ROLE_NAMES: dict[str, str] = {
    "ADMINISTRADOR": "Administrador",
    "SUPERVISOR": "Supervisor",
    "ARCHIVISTA": "Archivista",
    "DIGITALIZADOR": "Digitalizador",
    "CONSULTA": "Usuario de consulta",
}

PERMISSIONS: tuple[tuple[str, str, str], ...] = (
    ("users.read", "Consultar usuarios", "Listar y consultar usuarios."),
    ("users.create", "Crear usuarios", "Dar de alta usuarios."),
    ("users.update", "Actualizar usuarios", "Modificar datos de usuarios."),
    ("users.delete", "Desactivar usuarios", "Aplicar baja logica a usuarios."),
    ("users.lock", "Bloquear usuarios", "Bloquear o desbloquear cuentas."),
    (
        "users.reset_password",
        "Restablecer contrasenas",
        "Asignar una contrasena temporal y forzar cambio.",
    ),
    ("roles.read", "Consultar roles", "Listar roles y sus permisos."),
    ("roles.manage", "Gestionar roles", "Crear y modificar roles."),
    ("permissions.read", "Consultar permisos", "Listar el catalogo de permisos."),
    ("permissions.manage", "Gestionar permisos", "Crear permisos nuevos."),
    ("sessions.read", "Consultar sesiones", "Ver sesiones activas por usuario."),
    ("sessions.manage", "Revocar sesiones", "Revocar sesiones de cualquier usuario."),
    ("audit.read", "Consultar auditoria", "Leer eventos de seguridad y auditoria."),
    ("catalog.read", "Consultar catalogos", "Ver tribunales, areas y anaqueles."),
    ("catalog.manage", "Gestionar catalogos", "Crear y modificar catalogos."),
    ("search.read", "Busqueda global", "Ejecutar busquedas autorizadas."),
    ("boxes.read", "Consultar cajas", "Ver cajas y su ubicacion."),
    ("boxes.create", "Crear cajas", "Registrar cajas nuevas."),
    ("boxes.update", "Actualizar cajas", "Editar metadatos de cajas."),
    ("boxes.delete", "Dar de baja cajas", "Aplicar baja logica a cajas."),
    ("cases.read", "Consultar expedientes", "Ver expedientes judiciales."),
    ("cases.create", "Crear expedientes", "Registrar expedientes."),
    ("cases.update", "Actualizar expedientes", "Editar expedientes."),
    ("documents.read", "Consultar documentos", "Ver documentos administrativos."),
    ("documents.manage", "Gestionar documentos", "Crear y editar documentos."),
    ("files.read", "Consultar archivos", "Ver metadatos de archivos."),
    ("files.upload", "Subir archivos", "Cargar archivos al almacenamiento privado."),
    ("files.download", "Descargar archivos", "Descargar archivos autorizados."),
    ("imports.read", "Consultar importaciones", "Ver lotes de importacion."),
    ("imports.create", "Crear importaciones", "Cargar lotes de importacion."),
    ("imports.approve", "Aprobar importaciones", "Aprobar la aplicacion de un lote."),
    ("ocr.review", "Revisar OCR", "Validar y corregir resultados de OCR."),
    ("loans.read", "Consultar prestamos", "Ver prestamos y vencimientos."),
    ("loans.manage", "Gestionar prestamos", "Registrar y cerrar prestamos."),
    ("movements.read", "Consultar movimientos", "Ver traslados y devoluciones."),
    (
        "movements.manage",
        "Gestionar movimientos",
        "Registrar traslados y devoluciones.",
    ),
    ("inventory.read", "Consultar inventario", "Ver sesiones y diferencias."),
    ("inventory.manage", "Gestionar inventario", "Ejecutar conciliaciones."),
    ("reports.read", "Consultar reportes", "Ver reportes autorizados."),
    ("reports.export", "Exportar reportes", "Generar Excel, CSV y PDF."),
    ("settings.read", "Consultar configuracion", "Ver politicas del sistema."),
    ("settings.manage", "Gestionar configuracion", "Modificar politicas del sistema."),
)

ROLE_PERMISSIONS: dict[str, tuple[str, ...]] = {
    "ADMINISTRADOR": tuple(code for code, _, _ in PERMISSIONS),
    "SUPERVISOR": (
        "users.read",
        "roles.read",
        "permissions.read",
        "sessions.read",
        "sessions.manage",
        "audit.read",
        "catalog.read",
        "catalog.manage",
        "search.read",
        "boxes.read",
        "boxes.create",
        "boxes.update",
        "cases.read",
        "cases.create",
        "cases.update",
        "documents.read",
        "documents.manage",
        "files.read",
        "files.upload",
        "files.download",
        "imports.read",
        "imports.create",
        "imports.approve",
        "ocr.review",
        "loans.read",
        "loans.manage",
        "movements.read",
        "movements.manage",
        "inventory.read",
        "inventory.manage",
        "reports.read",
        "reports.export",
        "settings.read",
    ),
    "ARCHIVISTA": (
        "catalog.read",
        "search.read",
        "boxes.read",
        "boxes.create",
        "boxes.update",
        "cases.read",
        "cases.create",
        "cases.update",
        "documents.read",
        "documents.manage",
        "files.read",
        "files.upload",
        "files.download",
        "imports.read",
        "imports.create",
        "loans.read",
        "loans.manage",
        "movements.read",
        "movements.manage",
        "inventory.read",
        "inventory.manage",
        "reports.read",
    ),
    "DIGITALIZADOR": (
        "catalog.read",
        "search.read",
        "boxes.read",
        "cases.read",
        "documents.read",
        "files.read",
        "files.upload",
        "files.download",
        "imports.read",
        "imports.create",
        "ocr.review",
    ),
    "CONSULTA": (
        "catalog.read",
        "search.read",
        "boxes.read",
        "cases.read",
        "documents.read",
        "files.read",
        "files.download",
        "reports.read",
    ),
}


async def _ensure_role(session: AsyncSession, code: str, name: str) -> Role:
    role = await session.scalar(select(Role).where(Role.code == code))
    if role is None:
        role = Role(
            code=code,
            name=name,
            description=None,
            is_system=True,
            status=CatalogStatus.ACTIVE.value,
        )
        session.add(role)
        await session.flush()
        return role

    # Los roles creados por el seed antiguo pueden tener is_system=False.
    changed = False
    if not role.is_system:
        role.is_system = True
        changed = True
    if role.status != CatalogStatus.ACTIVE.value:
        role.status = CatalogStatus.ACTIVE.value
        changed = True
    if changed:
        await session.flush()
    return role


async def _ensure_permission(
    session: AsyncSession, code: str, name: str, description: str
) -> Permission:
    permission = await session.scalar(select(Permission).where(Permission.code == code))
    if permission is None:
        permission = Permission(code=code, name=name, description=description)
        session.add(permission)
        await session.flush()
        return permission

    changed = False
    if permission.name != name:
        permission.name = name
        changed = True
    if permission.description != description:
        permission.description = description
        changed = True
    if changed:
        await session.flush()
    return permission


async def seed_rbac(session: AsyncSession) -> None:
    """Aplica catalogo de permisos y matriz rol-permiso de forma idempotente.

    No elimina permisos ni asociaciones existentes: solo inserta lo que falta.
    El llamador es responsable del commit.
    """

    await session.execute(
        text("SELECT pg_advisory_xact_lock(:lock_key)"),
        {"lock_key": SEED_RBAC_LOCK_KEY},
    )

    roles = {
        code: await _ensure_role(session, code, name)
        for code, name in ROLE_NAMES.items()
    }
    permissions = {
        code: await _ensure_permission(session, code, name, description)
        for code, name, description in PERMISSIONS
    }

    rows = await session.execute(
        select(RolePermission.role_id, RolePermission.permission_id)
    )
    existing = {(row[0], row[1]) for row in rows.all()}

    for role_code, permission_codes in ROLE_PERMISSIONS.items():
        role = roles[role_code]
        for permission_code in permission_codes:
            key = (role.id, permissions[permission_code].id)
            if key in existing:
                continue
            session.add(
                RolePermission(
                    role_id=role.id,
                    permission_id=permissions[permission_code].id,
                    granted_by=None,
                )
            )
            existing.add(key)


async def main() -> None:
    settings = get_settings()
    database = Database(settings)
    try:
        async with database.session() as session:
            await seed_rbac(session)
            await session.commit()
    finally:
        await database.dispose()
    print("RBAC aplicado correctamente")  # noqa: T201


if __name__ == "__main__":
    asyncio.run(main(), loop_factory=asyncio.SelectorEventLoop)
```

### 17.5 Integrar con el seed existente

Modificar `backend/src/judicial_archive/db/seed.py`:

1. Añadir el import tras los imports de modelos:

```python
from judicial_archive.db.seed_rbac import seed_rbac
```

2. Llamar `seed_rbac` dentro de `seed_database`, justo antes del `commit` final:

```python
    await _ensure_party_role(session)
    await _ensure_numbering_policy(session)
    await _ensure_timezone_setting(session)

    # B4: permisos y matriz rol-permiso
    await seed_rbac(session)

    await session.commit()
```

> `seed_rbac` no importa `seed.py`, por lo que no hay ciclo. Mantener `ROLES` en `seed.py` y `ROLE_NAMES` en `seed_rbac.py` sincronizados; ambos son idempotentes y usan los mismos códigos.

### 17.6 Ejecutar el seed

```powershell
Set-Location C:\Users\Tony\Documents\sga\backend

# Opcion A: todo el seed (catalogos + RBAC)
uv run python -m judicial_archive.db.seed

# Opcion B: solo RBAC (roles, permisos y matriz)
uv run python -m judicial_archive.db.seed_rbac
```

Ambos comandos deben poder ejecutarse dos veces seguidas sin errores ni duplicados.

### 17.7 Verificación SQL

Con `psql` o cualquier cliente:

```sql
-- Total de permisos (debe coincidir con len(PERMISSIONS))
SELECT count(*) AS permisos FROM permissions;

-- Permisos por rol
SELECT r.code, count(rp.permission_id) AS permisos
FROM roles r
LEFT JOIN role_permissions rp ON rp.role_id = r.id
GROUP BY r.code
ORDER BY r.code;

-- El administrador debe tener todos los permisos
SELECT count(*) AS permisos_admin
FROM role_permissions rp
JOIN roles r ON r.id = rp.role_id
WHERE r.code = 'ADMINISTRADOR';

-- Duplicados (siempre 0)
SELECT role_id, permission_id, count(*)
FROM role_permissions
GROUP BY role_id, permission_id
HAVING count(*) > 1;
```

Resultado esperado: `permisos_admin = permisos`, cero duplicados y cinco roles.

### 17.8 Reglas de seguridad del seed

- **Nunca** insertar usuarios ni contraseñas en el seed. El único alta de administrador es `scripts/create_admin.py`.
- El seed es **aditivo**: no borra permisos ni asociaciones. Para retirar un permiso de un rol, usar la API (`POST /roles/{id}/permissions`) con auditoría.
- Si se renombra un código de permiso, crear una migración de datos revisable o una tarea de reconciliación; no dejar códigos huérfanos.
- Ejecutar el seed en cada despliegue es seguro por ser idempotente, pero debe hacerse dentro del procedimiento de despliegue y con respaldo previo.

---

## 18. Protección CSRF efectiva

### 18.1 Diseño

Se usa **double-submit cookie** con vínculo adicional a la sesión:

1. El cliente obtiene un token con `GET /api/v1/auth/csrf`. El servidor lo deja en la cookie `sga_csrf` (legible por JavaScript: `HttpOnly=false`) y lo devuelve en el cuerpo.
2. En todo método no idempotente (`POST`, `PUT`, `PATCH`, `DELETE`) el cliente envía el mismo valor en el header `X-CSRF-Token`.
3. El middleware compara header y cookie en tiempo constante.
4. En peticiones autenticadas, `get_current_user` comprueba además que el hash del header coincide con `auth_sessions.csrf_token_hash`. Así una cookie CSRF inyectada por un atacante no sirve aunque conozca el token.
5. El login **reutiliza** el token previamente emitido; no lo rota. Esto evita que el cliente tenga que refrescar el header justo después de autenticarse.
6. `SameSite=Lax` se mantiene como defensa en profundidad, pero no sustituye la validación.

Rutas exentas: `GET /api/v1/auth/csrf` (obviamente) y los métodos seguros `GET/HEAD/OPTIONS/TRACE`. `POST /api/v1/auth/login` **sí** exige CSRF.

### 18.2 Configuración

Los campos `auth_csrf_cookie_name`, `auth_csrf_header_name`, `auth_csrf_cookie_secure`,
`auth_csrf_cookie_httponly`, `auth_csrf_cookie_samesite`, `auth_csrf_cookie_path` y
`auth_csrf_max_age_seconds` **ya existen**. Solo falta el interruptor:

```python
    auth_csrf_enabled: bool = True
```

En el validador de producción (`_validate_auth_production`) añadir:

```python
    if not self.auth_csrf_enabled:
        problems.append("auth_csrf_enabled debe ser true en produccion")
```

En `backend/.env.example`, añadir:

```dotenv
SGA_AUTH_CSRF_ENABLED=true
```

> `SGA_AUTH_CSRF_ENABLED=false` solo se permite en `development`/`testing`. Producción falla al arrancar si está desactivado.

### 18.3 Crear el middleware

Añadir a `backend/src/judicial_archive/core/middleware.py`:

```python
from starlette.requests import Request

from judicial_archive.core.config import Settings
from judicial_archive.core.security import constant_time_compare


_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})


class CSRFMiddleware:
    """Valida double-submit cookie en metodos no idempotentes."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        settings: Settings,
        exempt_paths: tuple[str, ...] = (),
    ) -> None:
        self.app = app
        self.settings = settings
        self.exempt_paths = frozenset(exempt_paths)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not self.settings.auth_csrf_enabled:
            await self.app(scope, receive, send)
            return

        method = str(scope.get("method", "GET")).upper()
        path = str(scope.get("path", ""))
        if method in _SAFE_METHODS or path in self.exempt_paths:
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        cookie_token = request.cookies.get(self.settings.auth_csrf_cookie_name)
        header_token = request.headers.get(self.settings.auth_csrf_header_name)

        if (
            not cookie_token
            or not header_token
            or not constant_time_compare(cookie_token, header_token)
        ):
            await self._reject(scope, receive, send)
            return

        await self.app(scope, receive, send)

    async def _reject(self, scope: Scope, receive: Receive, send: Send) -> None:
        state = scope.get("state")
        request_id = state.get("request_id") if isinstance(state, dict) else None
        response: Response = build_error_response(
            status_code=403,
            code=ErrorCode.FORBIDDEN,
            message="Token CSRF ausente o invalido.",
            request_id=request_id if isinstance(request_id, str) else None,
            details={"reason": "csrf"},
        )
        await response(scope, receive, send)
```

Los imports `Response`, `ASGIApp`, `Receive`, `Scope`, `Send`, `ErrorCode` y `build_error_response` ya existen en ese archivo. Solo hay que añadir `Request`, `Settings` y `constant_time_compare`.

### 18.4 Endpoint para obtener el token

En `backend/src/judicial_archive/modules/auth/schemas.py`:

```python
class CsrfTokenResponse(BaseModel):
    csrf_token: str
```

En `backend/src/judicial_archive/modules/auth/services.py`, extraer el helper de cookie:

```python
def set_csrf_cookie(response: Response, settings: Settings, token: str) -> None:
    response.set_cookie(
        key=settings.auth_csrf_cookie_name,
        value=token,
        httponly=settings.auth_csrf_cookie_httponly,
        secure=settings.auth_csrf_cookie_secure,
        samesite=settings.auth_csrf_cookie_samesite,
        path=settings.auth_csrf_cookie_path,
        max_age=settings.auth_csrf_max_age_seconds,
    )


def _set_session_cookies(
    response: Response, settings: Settings, session_token: str, csrf_token: str
) -> None:
    response.set_cookie(
        key=settings.auth_session_cookie_name,
        value=session_token,
        httponly=settings.auth_session_cookie_httponly,
        secure=settings.auth_session_cookie_secure,
        samesite=settings.auth_session_cookie_samesite,
        path=settings.auth_session_cookie_path,
        max_age=settings.auth_session_max_age_seconds,
    )
    set_csrf_cookie(response, settings, csrf_token)
```

En `backend/src/judicial_archive/modules/auth/routers.py`:

```python
from judicial_archive.core.security import generate_csrf_token


@router.get("/csrf", response_model=schemas.CsrfTokenResponse)
async def csrf_token(
    request: Request,
    response: Response,
    settings: Settings = Depends(get_app_settings),
) -> schemas.CsrfTokenResponse:
    # No rotar un token existente: la sesion ya tiene su hash vinculado y
    # rotarlo invalidaria los POST de un cliente autenticado.
    token = request.cookies.get(settings.auth_csrf_cookie_name)
    if not token or len(token) < 32:
        token = generate_csrf_token()
        services.set_csrf_cookie(response, settings, token)
    return schemas.CsrfTokenResponse(csrf_token=token)
```

### 18.5 Vincular CSRF a la sesión

**a) En el login** (`modules/auth/services.py`), sustituir la generación de un token nuevo por el token ya validado por el middleware:

```python
    # El middleware ya verifico cookie == header. Se vincula el token a la
    # sesion para impedir que una cookie inyectada sea aceptada.
    csrf_token = request.cookies.get(settings.auth_csrf_cookie_name)
    if settings.auth_csrf_enabled and not csrf_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Token CSRF ausente"
        )
    if not csrf_token:
        csrf_token = generate_csrf_token()

    session_token = generate_session_token()
    token_hash = hash_opaque_token(session_token)
    csrf_hash = hash_opaque_token(csrf_token)
```

Mantener `generate_csrf_token` importado en `services.py` como fallback para desarrollo con CSRF
desactivado. La llamada `_set_session_cookies(response, settings, session_token, csrf_token)` se
mantiene y vuelve a dejar la misma cookie.

**b) En `api/deps.py`**, ampliar el import existente con `verify_opaque_token`:

```python
from judicial_archive.core.security import (
    hash_opaque_token,
    is_expired,
    verify_opaque_token,
)
```

y, tras validar que el usuario existe, está activo y no está bloqueado, insertar antes de
actualizar `last_seen_at`:

```python
    unsafe_methods = frozenset({"POST", "PUT", "PATCH", "DELETE"})
    if settings.auth_csrf_enabled and request.method.upper() in unsafe_methods:
        csrf_header = request.headers.get(settings.auth_csrf_header_name)
        if (
            not csrf_header
            or not auth_session.csrf_token_hash
            or not verify_opaque_token(csrf_header, auth_session.csrf_token_hash)
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Token CSRF invalido"
            )
```

Esto protege `logout`, `logout-all`, `change-password` y todos los endpoints de administración sin repetir código.

### 18.6 Registrar el middleware

En `backend/src/judicial_archive/main.py`:

1. Importar:

```python
from judicial_archive.core.middleware import (
    CSRFMiddleware,
    RequestBodyLimitMiddleware,
    RequestContextMiddleware,
    TrustedHostMiddleware,
)
```

2. Añadirlo **como primer middleware**, justo después de `app.include_router(...)` y antes de `RequestBodyLimitMiddleware`:

```python
    # CSRF es el middleware mas interno: los limites de cuerpo y host se
    # evaluan antes. Los metodos seguros no se ven afectados.
    app.add_middleware(
        CSRFMiddleware,
        settings=resolved_settings,
        exempt_paths=(f"{resolved_settings.api_v1_prefix}/auth/csrf",),
    )
```

El orden final (de exterior a interior) queda:
`RequestContext → CORS → TrustedHost → RequestBodyLimit → CSRF → rutas`.

Además, en la configuración de `CORSMiddleware`, sustituir `resolved_settings.csrf_header_name`
por `resolved_settings.auth_csrf_header_name` dentro de `allow_headers`, para que un nombre de
header personalizado no sea bloqueado por CORS.

### 18.7 Flujo del cliente

```text
GET  /api/v1/auth/csrf          -> 200 {"csrf_token": "..."} + cookie sga_csrf
POST /api/v1/auth/login         -> header X-CSRF-Token obligatorio
GET  /api/v1/auth/me            -> sin header (metodo seguro)
POST /api/v1/users/             -> header X-CSRF-Token obligatorio
POST /api/v1/auth/logout        -> header X-CSRF-Token obligatorio
```

Ejemplo PowerShell:

```powershell
$b = "http://127.0.0.1:8000/api/v1"

$csrf = (Invoke-RestMethod "$b/auth/csrf").csrf_token
$headers = @{ "X-CSRF-Token" = $csrf }

$body = @{ username = "admin"; password = "TuClaveLarga123" } | ConvertTo-Json
Invoke-RestMethod -Method Post "$b/auth/login" -ContentType "application/json" `
  -Body $body -Headers $headers -SessionVariable s

Invoke-RestMethod "$b/auth/me" -WebSession $s

Invoke-RestMethod -Method Post "$b/auth/logout" -Headers $headers -WebSession $s
```

En navegador, el token se lee de `document.cookie` (`sga_csrf`) o se conserva el valor devuelto por `/auth/csrf`. No guardar el token en `localStorage` si se puede evitar; mantenerlo en memoria.

### 18.8 Compatibilidad y despliegue

- Los clientes existentes deben llamar a `/auth/csrf` antes del primer `POST`. Es un cambio de contrato: documentarlo en `docs/api.md`.
- `TestClient` conserva cookies automáticamente; los tests deben pedir el token antes de cada login (ver sección 20).
- Si se despliega detrás de un proxy, no reescribir `Cookie` ni `X-CSRF-Token`.
- No eximir `/auth/login`: el login CSRF es un vector real (fijación de sesión del atacante).
- Un `403` con `details.reason == "csrf"` significa token ausente/desincronizado, no permisos insuficientes.
- `/auth/csrf` no rota un token existente: la sesión ya tiene su hash vinculado y rotarlo invalidaría los POST del cliente. Para recuperar una cookie desincronizada, cerrar sesión y volver a entrar.

---

## 19. Endpoints de roles, permisos y administración de usuarios

### 19.1 Estructura nueva

```text
backend/src/judicial_archive/modules/roles/
├── __init__.py
├── schemas.py
├── repositories.py
├── services.py
└── routers.py
```

Los modelos siguen en `modules/users/models.py` (`Role`, `Permission`, `RolePermission`) para no duplicar el mapeo ORM.

### 19.2 `modules/roles/schemas.py`

```python
from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

RoleStatus = Literal["ACTIVE", "INACTIVE"]


class PermissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    description: str | None


class RoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    description: str | None
    is_system: bool
    status: str
    permissions: list[str] = Field(default_factory=list)


class RoleCreate(BaseModel):
    code: str = Field(min_length=2, max_length=64, pattern=r"^[A-Z][A-Z0-9_]{1,63}$")
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)


class RoleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    status: RoleStatus | None = None


class AssignPermissions(BaseModel):
    permission_codes: list[str] = Field(default_factory=list)


class PermissionCreate(BaseModel):
    code: str = Field(
        min_length=3,
        max_length=100,
        pattern=r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$",
    )
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=500)


class MessageResponse(BaseModel):
    message: str
```

### 19.3 `modules/roles/repositories.py`

```python
from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.modules.users.models import Permission, Role, RolePermission


class RolesRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_roles(self) -> Sequence[Role]:
        res = await self.session.execute(select(Role).order_by(Role.code))
        return res.scalars().all()

    async def get_role_by_id(self, role_id: UUID) -> Role | None:
        res = await self.session.execute(select(Role).where(Role.id == role_id))
        return res.scalar_one_or_none()

    async def get_role_by_code(self, code: str) -> Role | None:
        res = await self.session.execute(select(Role).where(Role.code == code))
        return res.scalar_one_or_none()

    async def list_permissions(self) -> Sequence[Permission]:
        res = await self.session.execute(select(Permission).order_by(Permission.code))
        return res.scalars().all()

    async def get_permission_by_code(self, code: str) -> Permission | None:
        res = await self.session.execute(
            select(Permission).where(Permission.code == code)
        )
        return res.scalar_one_or_none()

    async def get_permissions_by_codes(self, codes: list[str]) -> Sequence[Permission]:
        if not codes:
            return []
        res = await self.session.execute(
            select(Permission).where(Permission.code.in_(codes))
        )
        return res.scalars().all()

    async def get_permission_codes_for_role(self, role_id: UUID) -> list[str]:
        res = await self.session.execute(
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id == role_id)
            .order_by(Permission.code)
        )
        return [row[0] for row in res.all()]

    async def replace_role_permissions(
        self,
        role_id: UUID,
        permission_ids: list[UUID],
        granted_by: UUID | None,
    ) -> None:
        await self.session.execute(
            delete(RolePermission).where(RolePermission.role_id == role_id)
        )
        await self.session.flush()
        for permission_id in permission_ids:
            self.session.add(
                RolePermission(
                    role_id=role_id,
                    permission_id=permission_id,
                    granted_by=granted_by,
                )
            )
```

### 19.4 `modules/roles/services.py`

```python
from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.core.enums import CatalogStatus
from judicial_archive.modules.auth.models import SecurityEvent
from judicial_archive.modules.roles import schemas
from judicial_archive.modules.roles.repositories import RolesRepository
from judicial_archive.modules.users.models import Permission, Role, User


async def list_roles(session: AsyncSession) -> list[dict[str, object]]:
    repo = RolesRepository(session)
    roles = await repo.list_roles()
    out: list[dict[str, object]] = []
    for role in roles:
        out.append(
            {
                "id": role.id,
                "code": role.code,
                "name": role.name,
                "description": role.description,
                "is_system": role.is_system,
                "status": role.status,
                "permissions": await repo.get_permission_codes_for_role(role.id),
            }
        )
    return out


async def create_role(
    request: Request,
    session: AsyncSession,
    actor: User,
    body: schemas.RoleCreate,
) -> dict[str, str]:
    repo = RolesRepository(session)
    code = body.code.strip().upper()
    if await repo.get_role_by_code(code):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="El rol ya existe"
        )

    role = Role(
        code=code,
        name=body.name.strip(),
        description=body.description.strip() if body.description else None,
        is_system=False,
        status=CatalogStatus.ACTIVE.value,
    )
    session.add(role)
    await session.flush()
    session.add(
        SecurityEvent(
            event_type="role_created",
            user_id=None,
            actor_id=actor.id,
            details={"role_code": role.code},
        )
    )
    await session.commit()
    return {"message": "Rol creado correctamente"}


async def update_role(
    request: Request,
    session: AsyncSession,
    actor: User,
    role_id: UUID,
    body: schemas.RoleUpdate,
) -> dict[str, str]:
    repo = RolesRepository(session)
    role = await repo.get_role_by_id(role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Rol no encontrado"
        )

    if role.is_system and body.status == CatalogStatus.INACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede desactivar un rol de sistema",
        )

    changed: list[str] = []
    if body.name is not None:
        role.name = body.name.strip()
        changed.append("name")
    if body.description is not None:
        role.description = body.description.strip() or None
        changed.append("description")
    if body.status is not None:
        role.status = body.status
        changed.append("status")

    session.add(
        SecurityEvent(
            event_type="role_updated",
            user_id=None,
            actor_id=actor.id,
            details={"role_code": role.code, "fields": changed},
        )
    )
    await session.commit()
    return {"message": "Rol actualizado correctamente"}


async def assign_permissions(
    request: Request,
    session: AsyncSession,
    actor: User,
    role_id: UUID,
    body: schemas.AssignPermissions,
) -> dict[str, str]:
    repo = RolesRepository(session)
    role = await repo.get_role_by_id(role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Rol no encontrado"
        )

    if role.code == "ADMINISTRADOR":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "El rol Administrador conserva el catalogo completo. "
                "Los permisos nuevos se aplican con el seed RBAC."
            ),
        )

    codes = sorted(
        {code.strip().lower() for code in body.permission_codes if code.strip()}
    )
    permissions = await repo.get_permissions_by_codes(codes)
    found = {permission.code for permission in permissions}
    unknown = sorted(set(codes) - found)
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Permisos desconocidos: {', '.join(unknown)}",
        )

    await repo.replace_role_permissions(
        role.id, [permission.id for permission in permissions], actor.id
    )
    session.add(
        SecurityEvent(
            event_type="role_permissions_updated",
            user_id=None,
            actor_id=actor.id,
            details={"role_code": role.code, "permissions": codes},
        )
    )
    await session.commit()
    return {"message": "Permisos del rol actualizados correctamente"}


async def list_permissions(session: AsyncSession) -> list[Permission]:
    repo = RolesRepository(session)
    return list(await repo.list_permissions())


async def create_permission(
    request: Request,
    session: AsyncSession,
    actor: User,
    body: schemas.PermissionCreate,
) -> dict[str, str]:
    repo = RolesRepository(session)
    code = body.code.strip().lower()
    if await repo.get_permission_by_code(code):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="El permiso ya existe"
        )

    permission = Permission(
        code=code,
        name=body.name.strip(),
        description=body.description.strip() if body.description else None,
    )
    session.add(permission)
    await session.flush()
    session.add(
        SecurityEvent(
            event_type="permission_created",
            user_id=None,
            actor_id=actor.id,
            details={"permission_code": permission.code},
        )
    )
    await session.commit()
    return {"message": "Permiso creado correctamente"}
```

### 19.5 `modules/roles/routers.py`

```python
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
    return await services.assign_permissions(
        request, session, current_user, role_id, body
    )


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
```

### 19.6 Extensiones del módulo usuarios

**a) `modules/users/schemas.py`** — añadir:

```python
from typing import Literal


class UserDetail(UserOut):
    permissions: list[str] = Field(default_factory=list)


class ResetPasswordRequest(BaseModel):
    new_password: str = Field(min_length=12, max_length=1024)
    must_change_password: bool = True
```

Y endurecer `UserUpdate`:

```python
class UserUpdate(BaseModel):
    email: EmailStr | None = None
    display_name: str | None = Field(default=None, min_length=1, max_length=160)
    status: Literal["ACTIVE", "INACTIVE", "SUSPENDED", "LOCKED"] | None = None
    must_change_password: bool | None = None
```

**b) `modules/users/repositories.py`** — añadir:

```python
from judicial_archive.modules.users.models import RolePermission


    async def get_role_codes(self, user_id: UUID) -> list[str]:
        res = await self.session.execute(
            select(Role.code)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
            .where(Role.status == "ACTIVE")
            .order_by(Role.code)
        )
        return [row[0] for row in res.all()]

    async def get_permission_codes(self, user_id: UUID) -> list[str]:
        res = await self.session.execute(
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(Role, Role.id == RolePermission.role_id)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
            .where(Role.status == "ACTIVE")
            .distinct()
            .order_by(Permission.code)
        )
        return [row[0] for row in res.all()]
```

**c) `modules/users/services.py`** — correcciones obligatorias.

Ampliar los imports del archivo:

```python
from fastapi import HTTPException, Request, status

from judicial_archive.core.config import Settings
from judicial_archive.modules.auth.repositories import AuthRepository
from judicial_archive.modules.users.schemas import ResetPasswordRequest
```

1. Validar códigos de rol al crear (no ignorar desconocidos):

```python
if body.role_codes:
    normalized = sorted({code.strip().upper() for code in body.role_codes})
    roles = await repo.get_roles_by_codes(normalized)
    found = {role.code for role in roles}
    unknown = sorted(set(normalized) - found)
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Roles desconocidos: {', '.join(unknown)}",
        )
    for role in roles:
        session.add(UserRole(user_id=user.id, role_id=role.id, assigned_by=actor.id))
```

2. Hacer lo mismo en `assign_roles` (validar **antes** de `remove_user_roles`) y añadir
protección contra auto-retirada del rol administrador:

```python
    normalized = sorted({code.strip().upper() for code in role_codes})
    roles = await repo.get_roles_by_codes(normalized)
    found = {role.code for role in roles}
    unknown = sorted(set(normalized) - found)
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Roles desconocidos: {', '.join(unknown)}",
        )

    if actor.id == user_id and "ADMINISTRADOR" not in found:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes retirarte tu propio rol Administrador",
        )
```

3. Evitar que un administrador se bloquee o se desactive a sí mismo:

```python
    if actor.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes bloquear tu propia cuenta",
        )
```

Añadir la misma guardia en `update_user` cuando `body.status` sea `INACTIVE`/`SUSPENDED`/`LOCKED`.

4. Añadir detalle y reset de contraseña (los imports ya se ampliaron arriba):

```python
async def get_user_detail(session: AsyncSession, user_id: UUID) -> dict[str, object]:
    repo = UsersRepository(session)
    user = await repo.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado"
        )
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "display_name": user.display_name,
        "status": user.status,
        "must_change_password": user.must_change_password,
        "failed_login_count": user.failed_login_count,
        "locked_until": user.locked_until,
        "last_login_at": user.last_login_at,
        "created_at": user.created_at,
        "roles": await repo.get_role_codes(user.id),
        "permissions": await repo.get_permission_codes(user.id),
    }


async def reset_password(
    request: Request,
    session: AsyncSession,
    settings: Settings,
    actor: User,
    user_id: UUID,
    body: ResetPasswordRequest,
) -> dict[str, str]:
    repo = UsersRepository(session)
    user = await repo.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado"
        )

    if len(body.new_password) < settings.auth_password_min_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "La nueva contrasena debe tener al menos "
                f"{settings.auth_password_min_length} caracteres"
            ),
        )

    user.password_hash = hash_password(body.new_password)
    user.password_changed_at = datetime.now(UTC)
    user.must_change_password = body.must_change_password
    user.failed_login_count = 0
    user.locked_until = None

    await AuthRepository(session).revoke_all_user_sessions(
        user.id, actor.id, "password_reset_by_admin"
    )
    session.add(
        SecurityEvent(
            event_type="password_reset_by_admin",
            user_id=user.id,
            actor_id=actor.id,
            details={"must_change_password": body.must_change_password},
        )
    )
    await session.commit()
    return {"message": "Contrasena restablecida correctamente"}
```

**d) `modules/users/routers.py`** — añadir imports y rutas:

```python
from judicial_archive.api.deps import get_app_settings
from judicial_archive.core.config import Settings
from judicial_archive.modules.auth import schemas as auth_schemas
from judicial_archive.modules.auth import services as auth_services


@router.get("/{user_id}", response_model=schemas.UserDetail)
async def get_user(
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.USERS_READ)),
) -> dict[str, object]:
    return await services.get_user_detail(session, user_id)


@router.post("/{user_id}/reset-password", response_model=schemas.MessageResponse)
async def reset_password(
    request: Request,
    user_id: UUID,
    body: schemas.ResetPasswordRequest,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_app_settings),
    current_user: User = Depends(require_permissions(permissions.USERS_RESET_PASSWORD)),
) -> dict[str, str]:
    return await services.reset_password(
        request, session, settings, current_user, user_id, body
    )
```

### 19.7 Sesiones por administrador

En `modules/auth/services.py` añadir `SessionInfo` al import de `modules.auth.schemas` y las
funciones siguientes:

```python
async def list_user_sessions(session: AsyncSession, user_id: UUID) -> list[SessionInfo]:
    res = await session.execute(
        select(AuthSession)
        .where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
        .order_by(AuthSession.created_at.desc())
    )
    return [
        SessionInfo(
            id=auth_session.id,
            created_at=auth_session.created_at,
            last_seen_at=auth_session.last_seen_at,
            expires_at=auth_session.expires_at,
            ip_address=str(auth_session.ip_address)
            if auth_session.ip_address
            else None,
            user_agent=auth_session.user_agent,
        )
        for auth_session in res.scalars().all()
    ]


async def revoke_user_session(
    request: Request,
    session: AsyncSession,
    actor: User,
    user_id: UUID,
    session_id: UUID,
) -> dict[str, str]:
    res = await session.execute(
        select(AuthSession).where(
            AuthSession.id == session_id,
            AuthSession.user_id == user_id,
        )
    )
    target = res.scalar_one_or_none()
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Sesion no encontrada"
        )

    if target.revoked_at is None:
        target.revoked_at = datetime.now(UTC)
        target.revoked_by = actor.id
        target.revocation_reason = "revoked_by_admin"

    session.add(
        SecurityEvent(
            event_type="session_revoked_by_admin",
            user_id=user_id,
            actor_id=actor.id,
            details={"session_id": str(session_id)},
        )
    )
    await session.commit()
    return {"message": "Sesion revocada correctamente"}
```

Añadir a `modules/users/routers.py`:

```python
@router.get(
    "/{user_id}/sessions",
    response_model=list[auth_schemas.SessionInfo],
)
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
```

`SessionInfo` no expone `token_hash`, IP completa ni datos sensibles adicionales.

### 19.8 Integrar routers

`backend/src/judicial_archive/api/v1/router.py`:

```python
from judicial_archive.modules.roles.routers import (
    permissions_router,
    router as roles_router,
)

api_router.include_router(roles_router)
api_router.include_router(permissions_router)
```

### 19.9 Contrato final de endpoints

| Método | Ruta | Permiso | Notas |
|---|---|---|---|
| GET | `/api/v1/auth/csrf` | — | Emite cookie/token CSRF |
| POST | `/api/v1/auth/login` | — | Requiere CSRF |
| POST | `/api/v1/auth/logout` | sesión | Requiere CSRF |
| POST | `/api/v1/auth/logout-all` | sesión | Requiere CSRF |
| GET | `/api/v1/auth/me` | sesión | Incluye roles y permisos |
| POST | `/api/v1/auth/change-password` | sesión | Requiere CSRF |
| GET | `/api/v1/users/` | `users.read` | Listado |
| POST | `/api/v1/users/` | `users.create` | Alta |
| GET | `/api/v1/users/{id}` | `users.read` | Detalle + permisos |
| PATCH | `/api/v1/users/{id}` | `users.update` | Datos/estado |
| POST | `/api/v1/users/{id}/lock` | `users.lock` | Bloqueo |
| POST | `/api/v1/users/{id}/unlock` | `users.lock` | Desbloqueo |
| POST | `/api/v1/users/{id}/roles` | `roles.manage` | Reemplaza roles |
| POST | `/api/v1/users/{id}/reset-password` | `users.reset_password` | Revoca sesiones |
| GET | `/api/v1/users/{id}/sessions` | `sessions.read` | Sesiones activas |
| POST | `/api/v1/users/{id}/sessions/{sid}/revoke` | `sessions.manage` | Revoca una |
| GET | `/api/v1/roles/` | `roles.read` | Roles + permisos |
| POST | `/api/v1/roles/` | `roles.manage` | Crear rol |
| PATCH | `/api/v1/roles/{id}` | `roles.manage` | Editar rol |
| POST | `/api/v1/roles/{id}/permissions` | `roles.manage` | Reemplaza permisos |
| GET | `/api/v1/permissions/` | `permissions.read` | Catálogo |
| POST | `/api/v1/permissions/` | `permissions.manage` | Crear permiso |

### 19.10 Reglas de seguridad

- El rol `ADMINISTRADOR` no se puede restringir por API; el seed garantiza el catálogo completo.
- No permitir que un actor se quite su propio rol `ADMINISTRADOR`, se bloquee o se desactive.
- Todo cambio de rol, permisos, contraseña o sesión genera `security_events` sin tokens ni contraseñas.
- Un reset de contraseña revoca todas las sesiones del usuario objetivo, incluida la actual si coincide.
- Los roles de sistema (`is_system=True`) no se pueden desactivar; sí renombrar su descripción visible.
- La creación de permisos por API es excepcional; el catálogo normal se versiona en `seed_rbac.py`.

---

## 20. Pruebas del cierre

### 20.1 Reglas de las pruebas

- Los tests que necesitan PostgreSQL/Redis llevan `@pytest.mark.integration` y usan los fixtures de `tests/integration/conftest.py`.
- Los tests de API usan `TestClient`, no `httpx.AsyncClient` (el resto de la suite ya usa `TestClient`).
- Cada test que hace un `POST` debe pedir `/api/v1/auth/csrf` y enviar `X-CSRF-Token`.
- Los tests de integración deben poder ejecutarse con `-n 0` porque comparten base de datos.
- No usar contraseñas reales ni datos de producción. Las contraseñas de prueba son ficticias.

### 20.2 `tests/unit/test_permissions_matrix.py`

```python
from __future__ import annotations

from judicial_archive.db.seed_rbac import (
    PERMISSIONS,
    ROLE_NAMES,
    ROLE_PERMISSIONS,
)


def test_permission_codes_are_unique() -> None:
    codes = [code for code, _, _ in PERMISSIONS]
    assert len(codes) == len(set(codes))


def test_every_role_has_a_permission_mapping() -> None:
    assert set(ROLE_PERMISSIONS) == set(ROLE_NAMES)


def test_role_permissions_only_reference_known_permissions() -> None:
    known = {code for code, _, _ in PERMISSIONS}
    for role_code, codes in ROLE_PERMISSIONS.items():
        unknown = set(codes) - known
        assert not unknown, f"{role_code} referencia permisos inexistentes: {unknown}"


def test_administrator_has_every_permission() -> None:
    admin = set(ROLE_PERMISSIONS["ADMINISTRADOR"])
    assert admin == {code for code, _, _ in PERMISSIONS}


def test_permission_format_matches_database_check() -> None:
    import re

    pattern = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")
    for code, _, _ in PERMISSIONS:
        assert pattern.fullmatch(code), code
```

### 20.3 `tests/unit/test_csrf_middleware.py`

```python
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from judicial_archive.core.config import Settings
from judicial_archive.core.middleware import CSRFMiddleware
from tests.helpers import build_test_settings


def _build_app(settings: Settings) -> FastAPI:
    app = FastAPI()

    @app.get("/read")
    def read() -> dict[str, bool]:
        return {"ok": True}

    @app.post("/mutate")
    def mutate() -> dict[str, bool]:
        return {"ok": True}

    @app.post("/api/v1/auth/csrf")
    def csrf_exempt() -> dict[str, bool]:
        return {"ok": True}

    app.add_middleware(
        CSRFMiddleware,
        settings=settings,
        exempt_paths=("/api/v1/auth/csrf",),
    )
    return app


def _client(settings: Settings) -> TestClient:
    return TestClient(_build_app(settings))


def test_safe_method_without_csrf_is_allowed() -> None:
    settings = build_test_settings()
    with _client(settings) as client:
        assert client.get("/read").status_code == 200


def test_unsafe_method_without_csrf_is_rejected() -> None:
    settings = build_test_settings()
    with _client(settings) as client:
        response = client.post("/mutate")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"
    assert response.json()["error"]["details"] == {"reason": "csrf"}


def test_unsafe_method_with_cookie_but_no_header_is_rejected() -> None:
    settings = build_test_settings()
    with _client(settings) as client:
        client.cookies.set(settings.auth_csrf_cookie_name, "token-value")
        response = client.post("/mutate")
    assert response.status_code == 403


def test_unsafe_method_with_mismatched_tokens_is_rejected() -> None:
    settings = build_test_settings()
    with _client(settings) as client:
        client.cookies.set(settings.auth_csrf_cookie_name, "cookie-value")
        response = client.post(
            "/mutate", headers={settings.auth_csrf_header_name: "header-value"}
        )
    assert response.status_code == 403


def test_unsafe_method_with_matching_tokens_is_allowed() -> None:
    settings = build_test_settings()
    token = "matching-token-value"
    with _client(settings) as client:
        client.cookies.set(settings.auth_csrf_cookie_name, token)
        response = client.post(
            "/mutate", headers={settings.auth_csrf_header_name: token}
        )
    assert response.status_code == 200


def test_exempt_path_is_allowed() -> None:
    settings = build_test_settings()
    with _client(settings) as client:
        response = client.post("/api/v1/auth/csrf")
    assert response.status_code == 200


def test_disabled_csrf_allows_unsafe_methods() -> None:
    settings = build_test_settings(auth_csrf_enabled=False)
    with _client(settings) as client:
        response = client.post("/mutate")
    assert response.status_code == 200
```

### 20.4 `tests/integration/auth_helpers.py`

```python
from __future__ import annotations

from collections.abc import Sequence

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from judicial_archive.core.enums import UserStatus
from judicial_archive.core.security import hash_password
from judicial_archive.db.seed_rbac import seed_rbac
from judicial_archive.modules.users.models import Role, User, UserRole

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "AdminPassword123!"
USER_PASSWORD = "UserPassword123!"


async def seed_user_with_role(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    username: str,
    password: str,
    role_code: str,
    display_name: str | None = None,
) -> None:
    async with session_factory() as session:
        await seed_rbac(session)
        role = await session.scalar(select(Role).where(Role.code == role_code))
        if role is None:
            raise AssertionError(f"Rol {role_code} no existe")

        user = User(
            username=username,
            username_normalized=username.lower(),
            email=None,
            email_normalized=None,
            display_name=display_name or username.title(),
            password_hash=hash_password(password),
            status=UserStatus.ACTIVE.value,
            must_change_password=False,
            failed_login_count=0,
        )
        session.add(user)
        await session.flush()
        session.add(UserRole(user_id=user.id, role_id=role.id, assigned_by=None))
        await session.commit()


async def seed_admin(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    username: str = ADMIN_USERNAME,
    password: str = ADMIN_PASSWORD,
) -> None:
    await seed_user_with_role(
        session_factory,
        username=username,
        password=password,
        role_code="ADMINISTRADOR",
        display_name="Administrador de prueba",
    )


def get_csrf(client: TestClient) -> str:
    response = client.get("/api/v1/auth/csrf")
    assert response.status_code == 200, response.text
    token = response.json()["csrf_token"]
    assert isinstance(token, str) and token
    return token


def csrf_headers(client: TestClient) -> dict[str, str]:
    token = client.cookies.get("sga_csrf")
    assert token
    return {"X-CSRF-Token": token}


def login(client: TestClient, username: str, password: str) -> None:
    token = get_csrf(client)
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
        headers={"X-CSRF-Token": token},
    )
    assert response.status_code == 200, response.text


def logout(client: TestClient) -> None:
    response = client.post("/api/v1/auth/logout", headers=csrf_headers(client))
    assert response.status_code == 200, response.text


def create_user(
    client: TestClient,
    *,
    username: str,
    password: str = USER_PASSWORD,
    role_codes: Sequence[str] = ("CONSULTA",),
) -> str:
    response = client.post(
        "/api/v1/users/",
        json={
            "username": username,
            "email": None,
            "display_name": username.title(),
            "password": password,
            "role_codes": list(role_codes),
            "must_change_password": False,
        },
        headers=csrf_headers(client),
    )
    assert response.status_code == 200, response.text
    listing = client.get("/api/v1/users/")
    assert listing.status_code == 200, listing.text
    for user in listing.json():
        if user["username"] == username:
            return str(user["id"])
    raise AssertionError(f"Usuario {username} no aparece en el listado")
```

### 20.5 `tests/integration/test_seed_rbac.py`

```python
from __future__ import annotations

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.db.seed_rbac import (
    PERMISSIONS,
    ROLE_PERMISSIONS,
    seed_rbac,
)
from judicial_archive.modules.users.models import Permission, Role, RolePermission


async def _count(session: AsyncSession, model: type[object]) -> int:
    value = await session.scalar(select(func.count()).select_from(model))
    return int(value or 0)


@pytest.mark.integration
async def test_seed_rbac_is_idempotent(db_session: AsyncSession) -> None:
    await seed_rbac(db_session)
    await db_session.commit()

    permissions = await _count(db_session, Permission)
    links = await _count(db_session, RolePermission)
    roles = await _count(db_session, Role)

    assert permissions == len(PERMISSIONS)
    assert links == sum(len(codes) for codes in ROLE_PERMISSIONS.values())
    assert roles == len(ROLE_PERMISSIONS)

    await seed_rbac(db_session)
    await db_session.commit()

    assert await _count(db_session, Permission) == permissions
    assert await _count(db_session, RolePermission) == links
    assert await _count(db_session, Role) == roles


@pytest.mark.integration
async def test_administrator_has_all_permissions(db_session: AsyncSession) -> None:
    await seed_rbac(db_session)
    await db_session.commit()

    result = await db_session.execute(
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(Role, Role.id == RolePermission.role_id)
        .where(Role.code == "ADMINISTRADOR")
    )
    admin_codes = set(result.scalars().all())
    assert admin_codes == {code for code, _, _ in PERMISSIONS}


@pytest.mark.integration
async def test_no_duplicate_role_permissions(db_session: AsyncSession) -> None:
    await seed_rbac(db_session)
    await db_session.commit()

    result = await db_session.execute(
        select(RolePermission.role_id, RolePermission.permission_id)
        .group_by(RolePermission.role_id, RolePermission.permission_id)
        .having(func.count() > 1)
    )
    assert result.all() == []
```

> `_count` recibe `type[object]`; si `mypy` se ejecuta sobre tests, cambiar a `type[Permission] | type[RolePermission] | type[Role]` o usar un `Type[Base]` de `judicial_archive.db.base`. No es obligatorio para la suite.

### 20.6 `tests/integration/test_csrf_flow.py`

```python
from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from judicial_archive.core.config import Settings
from judicial_archive.main import create_app
from tests.integration.auth_helpers import (
    ADMIN_PASSWORD,
    ADMIN_USERNAME,
    get_csrf,
    login,
    seed_admin,
)


@pytest_asyncio.fixture
async def api_client(
    migrated_database: str,
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> AsyncIterator[TestClient]:
    await seed_admin(session_factory)
    app = create_app(settings, configure_logs=False)
    with TestClient(app) as client:
        yield client


pytestmark = pytest.mark.integration


def test_login_without_csrf_is_rejected(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/v1/auth/login",
        json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
    )
    assert response.status_code == 403
    assert response.json()["error"]["details"] == {"reason": "csrf"}


def test_login_with_csrf_succeeds(api_client: TestClient) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    response = api_client.get("/api/v1/auth/me")
    assert response.status_code == 200
    assert response.json()["username"] == ADMIN_USERNAME


def test_mutation_without_header_is_rejected_after_login(
    api_client: TestClient,
) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    response = api_client.post(
        "/api/v1/users/",
        json={
            "username": "sin-csrf",
            "display_name": "Sin CSRF",
            "password": "UserPassword123!",
            "role_codes": ["CONSULTA"],
        },
    )
    assert response.status_code == 403
    assert response.json()["error"]["details"] == {"reason": "csrf"}


def test_safe_get_after_login_does_not_require_header(api_client: TestClient) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    assert api_client.get("/api/v1/users/").status_code == 200


def test_csrf_endpoint_returns_same_token_as_cookie(api_client: TestClient) -> None:
    token = get_csrf(api_client)
    assert api_client.cookies.get("sga_csrf") == token
```

### 20.7 `tests/integration/test_users_rbac_api.py`

```python
from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from judicial_archive.core.config import Settings
from judicial_archive.main import create_app
from tests.integration.auth_helpers import (
    ADMIN_PASSWORD,
    ADMIN_USERNAME,
    USER_PASSWORD,
    create_user,
    csrf_headers,
    login,
    logout,
    seed_admin,
)


@pytest_asyncio.fixture
async def api_client(
    migrated_database: str,
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> AsyncIterator[TestClient]:
    await seed_admin(session_factory)
    app = create_app(settings, configure_logs=False)
    with TestClient(app) as client:
        yield client


pytestmark = pytest.mark.integration


def _me(client: TestClient) -> dict[str, object]:
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 200, response.text
    return response.json()


def test_admin_can_create_and_list_users(api_client: TestClient) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    user_id = create_user(
        api_client, username="archivista1", role_codes=("ARCHIVISTA",)
    )
    assert user_id

    detail = api_client.get(f"/api/v1/users/{user_id}")
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["username"] == "archivista1"
    assert payload["roles"] == ["ARCHIVISTA"]
    assert "boxes.read" in payload["permissions"]


def test_create_user_with_unknown_role_returns_400(api_client: TestClient) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    response = api_client.post(
        "/api/v1/users/",
        json={
            "username": "rol-invalido",
            "display_name": "Rol Invalido",
            "password": USER_PASSWORD,
            "role_codes": ["NO_EXISTE"],
        },
        headers=csrf_headers(api_client),
    )
    assert response.status_code == 400
    assert "desconocidos" in response.json()["error"]["message"].lower()


def test_lock_and_unlock_user(api_client: TestClient) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    user_id = create_user(api_client, username="bloqueable")

    locked = api_client.post(
        f"/api/v1/users/{user_id}/lock", headers=csrf_headers(api_client)
    )
    assert locked.status_code == 200

    detail = api_client.get(f"/api/v1/users/{user_id}").json()
    assert detail["status"] == "LOCKED"

    unlocked = api_client.post(
        f"/api/v1/users/{user_id}/unlock", headers=csrf_headers(api_client)
    )
    assert unlocked.status_code == 200

    detail = api_client.get(f"/api/v1/users/{user_id}").json()
    assert detail["status"] == "ACTIVE"


def test_admin_cannot_lock_self(api_client: TestClient) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    admin_id = _me(api_client)["id"]
    response = api_client.post(
        f"/api/v1/users/{admin_id}/lock", headers=csrf_headers(api_client)
    )
    assert response.status_code == 400


def test_assign_unknown_role_returns_400(api_client: TestClient) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    user_id = create_user(api_client, username="roles-invalidos")
    response = api_client.post(
        f"/api/v1/users/{user_id}/roles",
        json={"role_codes": ["NO_EXISTE"]},
        headers=csrf_headers(api_client),
    )
    assert response.status_code == 400


def test_update_user_rejects_invalid_status(api_client: TestClient) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    user_id = create_user(api_client, username="estado-invalido")
    response = api_client.patch(
        f"/api/v1/users/{user_id}",
        json={"status": "BOGUS"},
        headers=csrf_headers(api_client),
    )
    assert response.status_code == 422


def test_consulta_role_cannot_list_users(api_client: TestClient) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    create_user(
        api_client,
        username="consulta1",
        password=USER_PASSWORD,
        role_codes=("CONSULTA",),
    )
    logout(api_client)

    login(api_client, "consulta1", USER_PASSWORD)
    response = api_client.get("/api/v1/users/")
    assert response.status_code == 403


def test_reset_password_revokes_sessions(api_client: TestClient) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    admin_id = _me(api_client)["id"]
    new_password = "NewAdminPassword123!"

    response = api_client.post(
        f"/api/v1/users/{admin_id}/reset-password",
        json={"new_password": new_password, "must_change_password": False},
        headers=csrf_headers(api_client),
    )
    assert response.status_code == 200

    assert api_client.get("/api/v1/auth/me").status_code == 401

    login(api_client, ADMIN_USERNAME, new_password)
    assert api_client.get("/api/v1/auth/me").status_code == 200


def test_admin_can_list_and_revoke_sessions(api_client: TestClient) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    admin_id = _me(api_client)["id"]

    sessions = api_client.get(f"/api/v1/users/{admin_id}/sessions")
    assert sessions.status_code == 200
    payload = sessions.json()
    assert payload
    session_id = payload[0]["id"]

    revoked = api_client.post(
        f"/api/v1/users/{admin_id}/sessions/{session_id}/revoke",
        headers=csrf_headers(api_client),
    )
    assert revoked.status_code == 200
    assert api_client.get("/api/v1/auth/me").status_code == 401


def test_change_password_revokes_other_sessions(api_client: TestClient) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    response = api_client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": ADMIN_PASSWORD,
            "new_password": "ChangedPassword123!",
        },
        headers=csrf_headers(api_client),
    )
    assert response.status_code == 200
    # La sesion actual se conserva; las demas se revocan.
    assert api_client.get("/api/v1/auth/me").status_code == 200
```

> Los mensajes de roles/permisos desconocidos se construyen como texto para que el manejador
> global de `HTTPException` los exponga en `error.message`; no usar `detail` como diccionario
> porque el sobre de error solo serializa texto en ese campo.

### 20.8 Actualizar pruebas existentes

**a) `tests/api/test_auth.py`** — dejar solo comprobaciones sin BD; el flujo real vive en
`tests/integration/`:

```python
from __future__ import annotations

from fastapi.testclient import TestClient


def test_me_requires_auth(client: TestClient) -> None:
    assert client.get("/api/v1/auth/me").status_code == 401


def test_csrf_endpoint_available_without_auth(client: TestClient) -> None:
    response = client.get("/api/v1/auth/csrf")
    assert response.status_code == 200
    assert response.json()["csrf_token"]
```

La prueba de credenciales inválidas se añade al archivo de integración del apartado b).

**b) `tests/integration/test_auth_flow.py`** — sustituir el placeholder por un flujo real:

```python
from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from judicial_archive.core.config import Settings
from judicial_archive.main import create_app
from tests.integration.auth_helpers import (
    ADMIN_PASSWORD,
    ADMIN_USERNAME,
    csrf_headers,
    get_csrf,
    login,
    seed_admin,
)


@pytest_asyncio.fixture
async def api_client(
    migrated_database: str,
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> AsyncIterator[TestClient]:
    await seed_admin(session_factory)
    app = create_app(settings, configure_logs=False)
    with TestClient(app) as client:
        yield client


pytestmark = pytest.mark.integration


def test_full_auth_flow(api_client: TestClient) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)

    me = api_client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["username"] == ADMIN_USERNAME
    assert "users.read" in me.json()["permissions"]

    logout = api_client.post("/api/v1/auth/logout", headers=csrf_headers(api_client))
    assert logout.status_code == 200
    assert api_client.get("/api/v1/auth/me").status_code == 401


def test_login_wrong_credentials(api_client: TestClient) -> None:
    token = get_csrf(api_client)
    response = api_client.post(
        "/api/v1/auth/login",
        json={"username": "noexiste", "password": "wrongpass123456"},
        headers={"X-CSRF-Token": token},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"
```

### 20.9 Comandos de prueba

```powershell
Set-Location C:\Users\Tony\Documents\sga\backend

# 1) Unitarias puras (sin BD)
uv run pytest tests/unit/test_permissions_matrix.py tests/unit/test_csrf_middleware.py -q

# 2) Integracion con PostgreSQL/Redis reales
$env:RUN_INTEGRATION = "1"
$env:TEST_DATABASE_URL = "postgresql+psycopg://postgres:Santi.15@localhost:5432/sga_test"
$env:TEST_REDIS_URL = "redis://localhost:6379/15"

uv run pytest tests/integration/test_seed_rbac.py -q -n 0
uv run pytest tests/integration/test_csrf_flow.py -q -n 0
uv run pytest tests/integration/test_users_rbac_api.py -q -n 0
uv run pytest tests/integration/test_auth_flow.py -q -n 0

# 3) Suite completa (obligatorio -n 0: los tests comparten BD)
uv run pytest -q -n 0

# 4) Cobertura por modulo nuevo
uv run pytest tests/unit/test_permissions_matrix.py tests/unit/test_csrf_middleware.py `
  tests/integration/test_seed_rbac.py tests/integration/test_csrf_flow.py `
  tests/integration/test_users_rbac_api.py -n 0 `
  --cov=judicial_archive.db.seed_rbac `
  --cov=judicial_archive.core.middleware `
  --cov=judicial_archive.modules.roles `
  --cov=judicial_archive.modules.users `
  --cov-report=term-missing
```

Cobertura objetivo:

| Módulo | Objetivo |
|---|---|
| `db/seed_rbac.py` | `>= 95 %` |
| `core/middleware.py` (CSRF) | `>= 90 %` |
| `modules/roles/*` | `>= 90 %` |
| `modules/users/services.py` | `>= 85 %` |
| Global del proyecto | `>= 75 %` (umbral vigente en `pyproject.toml`) |

---

## 21. Documentación a publicar

Los cuatro documentos siguientes deben quedar en el repositorio. El contenido está listo para copiar; ajustar nombres de host/puerto al entorno real.

### 21.1 `docs/api.md` — sección «Autenticación (B4)»

````markdown
## Autenticación (B4)

Base: `http://127.0.0.1:8000/api/v1` (desarrollo).
Las respuestas de error usan el sobre `{"error": {"code", "message", "details", "request_id"}}`.

### Cookies

| Cookie | HttpOnly | Uso |
|---|---|---|
| `sga_session` | Sí | Token opaco de sesión (solo se guarda su SHA-256 en BD) |
| `sga_csrf` | No | Token CSRF double-submit |

En producción ambas cookies usan `Secure=true`; `SameSite` es configurable (`lax` por defecto).

### Flujo

1. `GET /auth/csrf` → devuelve `{"csrf_token": "..."}` y fija la cookie `sga_csrf`.
2. `POST /auth/login` con `{"username","password"}` y header `X-CSRF-Token`.
3. El servidor fija `sga_session` y vincula el hash del token CSRF a la sesión.
4. En todo `POST/PUT/PATCH/DELETE` enviar `X-CSRF-Token` con el valor de `sga_csrf`.
5. `POST /auth/logout` revoca la sesión actual; `POST /auth/logout-all` revoca todas.

### Endpoints

| Método | Ruta | Permiso | Descripción |
|---|---|---|---|
| GET | `/auth/csrf` | — | Emite token CSRF |
| POST | `/auth/login` | — | Inicia sesión (requiere CSRF) |
| POST | `/auth/logout` | sesión | Cierra la sesión actual |
| POST | `/auth/logout-all` | sesión | Cierra todas las sesiones |
| GET | `/auth/me` | sesión | Usuario actual, roles y permisos |
| POST | `/auth/change-password` | sesión | Cambia contraseña y revoca otras sesiones |
| GET | `/users/` | `users.read` | Lista usuarios |
| POST | `/users/` | `users.create` | Crea usuario |
| GET | `/users/{id}` | `users.read` | Detalle con roles y permisos |
| PATCH | `/users/{id}` | `users.update` | Actualiza datos/estado |
| POST | `/users/{id}/lock` | `users.lock` | Bloquea cuenta |
| POST | `/users/{id}/unlock` | `users.lock` | Desbloquea cuenta |
| POST | `/users/{id}/roles` | `roles.manage` | Reemplaza roles |
| POST | `/users/{id}/reset-password` | `users.reset_password` | Contraseña temporal + revocación |
| GET | `/users/{id}/sessions` | `sessions.read` | Sesiones activas |
| POST | `/users/{id}/sessions/{sid}/revoke` | `sessions.manage` | Revoca una sesión |
| GET | `/roles/` | `roles.read` | Roles con sus permisos |
| POST | `/roles/` | `roles.manage` | Crea rol |
| PATCH | `/roles/{id}` | `roles.manage` | Edita rol |
| POST | `/roles/{id}/permissions` | `roles.manage` | Reemplaza permisos del rol |
| GET | `/permissions/` | `permissions.read` | Catálogo de permisos |
| POST | `/permissions/` | `permissions.manage` | Crea permiso |

### Ejemplos

```bash
# Obtener CSRF
curl -c cookies.txt http://127.0.0.1:8000/api/v1/auth/csrf

# Login (usar el valor devuelto por /auth/csrf)
curl -b cookies.txt -c cookies.txt \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: <TOKEN>" \
  -d '{"username":"admin","password":"..."}' \
  http://127.0.0.1:8000/api/v1/auth/login

# Consultar usuario actual
curl -b cookies.txt http://127.0.0.1:8000/api/v1/auth/me
```

```javascript
async function api(path, options = {}) {
  const method = (options.method || "GET").toUpperCase();
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };

  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
    const csrf = document.cookie
      .split("; ")
      .find((row) => row.startsWith("sga_csrf="))
      ?.split("=")[1];
    if (!csrf) throw new Error("Falta el token CSRF");
    headers["X-CSRF-Token"] = decodeURIComponent(csrf);
  }

  const response = await fetch(`/api/v1${path}`, {
    ...options,
    method,
    headers,
    credentials: "include",
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body?.error?.message || `HTTP ${response.status}`);
  }
  return response.status === 204 ? null : response.json();
}
```

### Códigos relevantes

| Estado | Significado |
|---|---|
| 401 | No autenticado, sesión expirada o cuenta bloqueada |
| 403 | Permisos insuficientes o CSRF ausente/inválido |
| 409 | Conflicto de unicidad (usuario, email, rol o permiso) |
| 422 | Datos inválidos |

`error.details.reason == "csrf"` indica problema de CSRF, no de permisos.
````

### 21.2 `docs/roles-y-permisos.md`

```markdown
# Roles y permisos

## Principios

- La autorización se verifica siempre en el servidor por permiso, no solo por rol.
- Mínimo privilegio y denegación por defecto.
- Los roles de sistema no se eliminan ni se desactivan.
- El rol `ADMINISTRADOR` conserva el catálogo completo de permisos.
- Todo cambio de roles o permisos se audita en `security_events`.

## Roles iniciales

| Código | Nombre | Uso |
|---|---|---|
| `ADMINISTRADOR` | Administrador | Control total |
| `SUPERVISOR` | Supervisor | Operación y supervisión, sin gestión de usuarios |
| `ARCHIVISTA` | Archivista | Cajas, expedientes, movimientos, préstamos |
| `DIGITALIZADOR` | Digitalizador | Carga y OCR |
| `CONSULTA` | Usuario de consulta | Solo lectura autorizada |

## Catálogo de permisos

Formato: `modulo.accion` (`^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$`).

- Usuarios: `users.read`, `users.create`, `users.update`, `users.delete`, `users.lock`,
  `users.reset_password`.
- Roles/permisos: `roles.read`, `roles.manage`, `permissions.read`, `permissions.manage`.
- Sesiones/auditoría: `sessions.read`, `sessions.manage`, `audit.read`.
- Catálogos/búsqueda: `catalog.read`, `catalog.manage`, `search.read`.
- Cajas/expedientes: `boxes.read/create/update/delete`, `cases.read/create/update`.
- Documentos/archivos: `documents.read`, `documents.manage`, `files.read`, `files.upload`,
  `files.download`.
- Operación: `imports.read/create/approve`, `ocr.review`, `loans.read/manage`,
  `movements.read/manage`, `inventory.read/manage`.
- Reportes/configuración: `reports.read`, `reports.export`, `settings.read`, `settings.manage`.

La fuente de verdad del catálogo y de la matriz es `src/judicial_archive/db/seed_rbac.py`.

## Matriz resumida

| Capacidad | ADMINISTRADOR | SUPERVISOR | ARCHIVISTA | DIGITALIZADOR | CONSULTA |
|---|:---:|:---:|:---:|:---:|:---:|
| Gestionar usuarios/roles/permisos | Sí | No | No | No | No |
| Ver usuarios, roles y sesiones | Sí | Sí | No | No | No |
| Revocar sesiones | Sí | Sí | No | No | No |
| Ver auditoría | Sí | Sí | No | No | No |
| Catálogos físicos | Sí | Gestionar | Consultar | Consultar | Consultar |
| Cajas y expedientes | Sí | Crear/editar | Crear/editar | Consultar | Consultar |
| Documentos y archivos | Sí | Gestionar | Gestionar | Consultar/subir | Consultar/descargar |
| Importaciones/OCR | Sí | Aprobar | Crear | Crear/revisar | No |
| Préstamos/movimientos/inventario | Sí | Gestionar | Gestionar | No | No |
| Reportes | Sí | Exportar | Consultar | No | Consultar |
| Configuración global | Sí | Consultar | No | No | No |

## Cómo se aplica

1. `get_current_user` valida la cookie `sga_session` y la sesión en `auth_sessions`.
2. `require_permissions("modulo.accion")` consulta `role_permissions` en cada petición.
3. Un usuario sin el permiso recibe `403` con `error.code = "forbidden"`.
4. `GET /auth/me` devuelve los roles y permisos efectivos para que el frontend muestre
   u oculte acciones; ocultar un botón no sustituye la validación del servidor.

## Administración

- Alta inicial: `uv run python scripts/create_admin.py` (interactivo, sin contraseña por defecto).
- Seed: `uv run python -m judicial_archive.db.seed_rbac` (idempotente).
- Roles/permisos por API: `GET/POST /roles/`, `POST /roles/{id}/permissions`,
  `GET/POST /permissions/`.
- El rol `ADMINISTRADOR` no se puede restringir por API.

## Cuentas iniciales

No crear usuarios por migración ni con contraseñas en el repositorio. Las cuentas se crean
con el script o por API y deben cambiar la contraseña en el primer acceso cuando corresponda.
```

### 21.3 `docs/seguridad.md` — sección B4

```markdown
## Autenticación y sesiones (B4)

### Contraseñas

- Hash Argon2id con `pwdlib.PasswordHash.recommended()`.
- Longitud mínima configurable (`SGA_AUTH_PASSWORD_MIN_LENGTH`, 12 por defecto).
- Nunca se registran contraseñas, hashes ni tokens en logs/auditoría.

### Sesiones

- Token opaco de alta entropía; en BD solo se almacena `sha256(token)`.
- Expiración por inactividad (`SGA_AUTH_SESSION_IDLE_MINUTES`) y absoluta
  (`SGA_AUTH_SESSION_ABSOLUTE_HOURS`).
- Revocación en logout, logout-all, cambio de contraseña, reset por administrador y
  revocación individual.
- Cookies `HttpOnly`, `Secure` en producción y `SameSite` configurable.

### CSRF

- Double-submit cookie + header `X-CSRF-Token`.
- Validación en todos los métodos no idempotentes, incluido el login.
- El token se vincula a la sesión mediante `auth_sessions.csrf_token_hash`.
- Comparación en tiempo constante.
- `GET /auth/csrf` es la única ruta exenta (método seguro).

### Fuerza bruta

- Intentos fallidos en `login_attempts` y `users.failed_login_count`.
- Bloqueo temporal tras `SGA_AUTH_LOGIN_MAX_ATTEMPTS` en la ventana configurada.
- Mensaje genérico «Credenciales inválidas»: no revelar si el usuario existe.

### Auditoría

- `security_events` registra login correcto/fallido, logout, revocaciones, cambios de
  contraseña, altas/bajas de usuarios y cambios de roles/permisos.
- Nunca se guardan secretos, tokens, hashes de sesión ni contraseñas.
- El detalle se limita a identificadores y códigos necesarios.

### Producción

- `SGA_AUTH_SESSION_COOKIE_SECURE=true`.
- `SGA_AUTH_CSRF_COOKIE_SECURE=true` y `SGA_AUTH_CSRF_ENABLED=true`.
- HTTPS obligatorio; no exponer la API por HTTP.
- CORS restringido a orígenes conocidos.
- Secretos en variables de entorno o gestor de secretos, nunca en Git.
- Revisar y rotar `SGA_SECRET_KEY` según política institucional.
- Restringir el acceso a PostgreSQL y Redis por red.
- Ejecutar el seed RBAC en cada despliegue y verificar el catálogo.
- Probar restauración de copias y plan de revocación de sesiones ante incidentes.

### Respuesta ante incidentes

1. Revocar sesiones del usuario afectado (`POST /users/{id}/sessions/{sid}/revoke` o
   `logout-all`).
2. Resetear contraseña (`POST /users/{id}/reset-password`).
3. Revisar `security_events` y `login_attempts`.
4. Si hay sospecha de escalado, revisar `user_roles` y `role_permissions`.
5. Documentar el incidente y las acciones en `docs/decisiones/`.
```

### 21.4 `docs/pruebas.md` — sección B4

````markdown
## Pruebas de autenticación y RBAC (B4)

### Variables de entorno

```powershell
$env:RUN_INTEGRATION = "1"
$env:TEST_DATABASE_URL = "postgresql+psycopg://postgres:Santi.15@localhost:5432/sga_test"
$env:TEST_REDIS_URL = "redis://localhost:6379/15"
```

`tests/integration/conftest.py` omite los tests si `RUN_INTEGRATION != "1"` o falta
`TEST_DATABASE_URL`. Nunca usar una base de producción.

### Comandos

```powershell
Set-Location backend

# Unitarias
uv run pytest tests/unit/test_permissions_matrix.py tests/unit/test_csrf_middleware.py -q

# Integración (siempre -n 0)
uv run pytest tests/integration/test_seed_rbac.py -q -n 0
uv run pytest tests/integration/test_csrf_flow.py -q -n 0
uv run pytest tests/integration/test_users_rbac_api.py -q -n 0
uv run pytest tests/integration/test_auth_flow.py -q -n 0

# Suite completa
uv run pytest -q -n 0

# Calidad
uv run ruff check .
uv run ruff format --check .
uv run mypy src
```

### Matriz de pruebas

| Área | Archivo | Qué cubre |
|---|---|---|
| Matriz de permisos | `tests/unit/test_permissions_matrix.py` | Unicidad, formato, admin completo |
| CSRF | `tests/unit/test_csrf_middleware.py` | Métodos seguros, token ausente/desigual, exención |
| Seed RBAC | `tests/integration/test_seed_rbac.py` | Idempotencia, totales, admin completo |
| CSRF real | `tests/integration/test_csrf_flow.py` | Login sin/con token, mutación sin header |
| Usuarios/RBAC | `tests/integration/test_users_rbac_api.py` | 403 por rol, CRUD, lock/unlock, reset, sesiones |
| Flujo auth | `tests/integration/test_auth_flow.py` | Login, me, logout |

### Cobertura

Umbral global: `75 %` (`fail_under` en `pyproject.toml`). Objetivo del cierre:
`>= 95 %` en `db/seed_rbac.py`, `>= 90 %` en CSRF y `modules/roles`, `>= 85 %` en
`modules/users/services.py`.

### Datos de prueba

- Contraseñas ficticias de al menos 12 caracteres.
- Nunca datos judiciales reales.
- La base de pruebas se trunca entre tests; no depender del orden.
- Los tests que comparten BD no deben ejecutarse con `-n auto`.
````

### 21.5 Otros documentos a tocar

- `README.md` del backend: añadir `/auth/csrf` al quickstart y el comando del seed RBAC.
- `docs/instalacion-desarrollo.md`: incluir `python -m judicial_archive.db.seed_rbac` tras las migraciones.
- `docs/decisiones/ADR-*.md`: registrar la decisión «CSRF double-submit + vínculo de sesión».
- `docs/pendientes-de-validacion.md`: registrar si el negocio quiere permitir que `SUPERVISOR` gestione usuarios (hoy no).

---

## 22. Validación integral y aceptación

### 22.1 Preflight

```powershell
Set-Location C:\Users\Tony\Documents\sga
git status --short
git log --oneline -3

Set-Location backend
uv sync
uv run python -c "import pwdlib, fastapi, sqlalchemy, alembic; print('deps ok')"
```

Comprobar PostgreSQL y Redis:

```powershell
$env:SGA_DATABASE_URL = "postgresql+psycopg://sga_dev:Dakota5544@localhost:5432/sga_dev"
uv run alembic current
```

### 22.2 Migraciones

Este bloque **no requiere una migración nueva**: las tablas `permissions`, `roles`,
`role_permissions`, `auth_sessions`, `login_attempts` y `security_events` ya existen en
`alembic/versions/88ae4fe9cb05_auth_rbac_sessions_security.py`. El seed es dato, no esquema.

```powershell
uv run alembic upgrade head
uv run alembic check
```

Si `alembic check` detecta diferencias, revisar los modelos antes de continuar. No generar
una migración para insertar permisos: eso se hace con el seed idempotente.

### 22.3 Aplicar seed y crear administrador

```powershell
# Catalogo completo + matriz rol-permiso (idempotente)
uv run python -m judicial_archive.db.seed_rbac

# Alternativa: seed completo (catalogos judiciales + RBAC)
uv run python -m judicial_archive.db.seed

# Alta segura de administrador (interactivo, sin contrasena por defecto)
uv run python scripts/create_admin.py
```

Orden correcto: migraciones → seed → alta de administrador → arranque del servidor.

### 22.4 Arrancar el servidor

```powershell
uv run uvicorn judicial_archive.asgi:app --reload --host 127.0.0.1 --port 8000 `
  --loop judicial_archive.core.runtime:selector_loop_factory
```

Abrir `http://127.0.0.1:8000/docs` y verificar que aparecen las etiquetas
`Autenticacion`, `Usuarios`, `Roles` y `Permisos`.

### 22.5 Prueba de humo manual (PowerShell)

```powershell
$b = "http://127.0.0.1:8000/api/v1"

# 1) Salud
Invoke-RestMethod "$b/health/live"
Invoke-RestMethod "$b/health/ready"

# 2) CSRF (guardar la cookie en la sesion de PowerShell)
$csrfResponse = Invoke-RestMethod "$b/auth/csrf" -SessionVariable s
$csrf = $csrfResponse.csrf_token
$h = @{ "X-CSRF-Token" = $csrf }

# 3) Login
$login = @{ username = "admin"; password = "TuClaveLarga123" } | ConvertTo-Json
Invoke-RestMethod -Method Post "$b/auth/login" -ContentType "application/json" `
  -Body $login -Headers $h -WebSession $s

# 4) Usuario actual (roles y permisos)
Invoke-RestMethod "$b/auth/me" -WebSession $s

# 5) Listar roles y permisos
Invoke-RestMethod "$b/roles/" -WebSession $s
Invoke-RestMethod "$b/permissions/" -WebSession $s

# 6) Crear usuario
$nuevo = @{
  username = "archivista1"
  email = "archivista1@ejemplo.com"
  display_name = "Archivista Uno"
  password = "OtraClaveLarga123"
  role_codes = @("ARCHIVISTA")
  must_change_password = $true
} | ConvertTo-Json
Invoke-RestMethod -Method Post "$b/users/" -ContentType "application/json" `
  -Body $nuevo -Headers $h -WebSession $s

# 7) Detalle, bloqueo y desbloqueo (usar el id devuelto por GET /users/)
$users = Invoke-RestMethod "$b/users/" -WebSession $s
$id = ($users | Where-Object { $_.username -eq "archivista1" }).id

Invoke-RestMethod "$b/users/$id" -WebSession $s
Invoke-RestMethod -Method Post "$b/users/$id/lock" -Headers $h -WebSession $s
Invoke-RestMethod -Method Post "$b/users/$id/unlock" -Headers $h -WebSession $s

# 8) Sesiones del administrador y revocacion
$me = Invoke-RestMethod "$b/auth/me" -WebSession $s
$sessions = Invoke-RestMethod "$b/users/$($me.id)/sessions" -WebSession $s
$sid = $sessions[0].id
Invoke-RestMethod -Method Post "$b/users/$($me.id)/sessions/$sid/revoke" -Headers $h -WebSession $s

# 9) Tras revocar, /auth/me debe devolver 401
try { Invoke-RestMethod "$b/auth/me" -WebSession $s } catch { $_.Exception.Response.StatusCode.value__ }

# 10) Login de nuevo y logout
Invoke-RestMethod -Method Post "$b/auth/login" -ContentType "application/json" `
  -Body $login -Headers $h -WebSession $s
Invoke-RestMethod -Method Post "$b/auth/logout" -Headers $h -WebSession $s
```

Pruebas negativas obligatorias:

```powershell
# Login sin CSRF -> 403 (no enviar cookie/header CSRF)
try { Invoke-RestMethod -Method Post "$b/auth/login" -ContentType "application/json" -Body $login } `
catch { $_.Exception.Response.StatusCode.value__ }

# Tras el logout anterior, obtener un CSRF nuevo y volver a autenticarse
$csrfResponse = Invoke-RestMethod "$b/auth/csrf" -WebSession $s
$csrf = $csrfResponse.csrf_token
$h = @{ "X-CSRF-Token" = $csrf }
Invoke-RestMethod -Method Post "$b/auth/login" -ContentType "application/json" `
  -Body $login -Headers $h -WebSession $s

# Mutacion autenticada sin header CSRF -> 403
try { Invoke-RestMethod -Method Post "$b/users/$id/lock" -WebSession $s } `
catch { $_.Exception.Response.StatusCode.value__ }
```

### 22.6 Puertas de calidad

```powershell
Set-Location C:\Users\Tony\Documents\sga\backend

uv run ruff check .
uv run ruff format --check .
uv run mypy src

$env:RUN_INTEGRATION = "1"
$env:TEST_DATABASE_URL = "postgresql+psycopg://postgres:Santi.15@localhost:5432/sga_test"
$env:TEST_REDIS_URL = "redis://localhost:6379/15"
uv run pytest -q -n 0
```

Resultados esperados:

| Comprobación | Resultado |
|---|---|
| `ruff check .` | `All checks passed!` |
| `ruff format --check .` | Sin archivos pendientes |
| `mypy src` | `Success: no issues found` |
| Suite completa | Todas pasan (136 previas + nuevas), sin fallos |
| Cobertura global | `>= 75 %` (objetivo real `>= 85 %`) |

Si `pytest` falla por el warning de Pydantic, ejecutar con:

```powershell
uv run pytest -q -n 0 `
  --override-ini="filterwarnings=ignore::pydantic.warnings.PydanticDeprecatedSince20"
```

No declarar B4 cerrada si algún comando no se ejecutó. Indicar la limitación.

### 22.7 Matriz de trazabilidad

| Requisito | Archivo(s) | Prueba |
|---|---|---|
| Permisos y matriz rol-permiso | `db/seed_rbac.py`, `modules/users/permissions.py` | `test_permissions_matrix.py`, `test_seed_rbac.py` |
| CSRF en métodos no idempotentes | `core/middleware.py`, `main.py` | `test_csrf_middleware.py`, `test_csrf_flow.py` |
| CSRF vinculado a sesión | `auth/services.py`, `api/deps.py` | `test_csrf_flow.py` |
| Administración de roles | `modules/roles/*` | `test_users_rbac_api.py` |
| Administración de usuarios | `modules/users/*` | `test_users_rbac_api.py` |
| Reset de contraseña | `modules/users/services.py` | `test_users_rbac_api.py` |
| Revocación de sesiones | `modules/auth/services.py` | `test_users_rbac_api.py` |
| Alta segura de administrador | `scripts/create_admin.py` | Prueba manual 22.5 |
| Auditoría sin secretos | `modules/auth/models.py`, servicios | Revisión de `security_events` |

### 22.8 Checklist de aceptación del cierre

#### Seed RBAC

- [ ] `db/seed_rbac.py` creado con catálogo y matriz
- [ ] `seed.py` invoca `seed_rbac`
- [ ] `python -m judicial_archive.db.seed_rbac` ejecutado dos veces sin duplicados
- [ ] Administrador con todos los permisos
- [ ] Usuario `CONSULTA` recibe `403` en `/users/`

#### CSRF

- [ ] `auth_csrf_enabled` en configuración y validador de producción
- [ ] `CSRFMiddleware` registrado como middleware interno
- [ ] `GET /auth/csrf` emite cookie y token
- [ ] Login exige `X-CSRF-Token`
- [ ] `get_current_user` vincula el token a `auth_sessions.csrf_token_hash`
- [ ] Mutaciones sin token devuelven `403`

#### Roles y permisos

- [ ] `GET/POST /roles/` funcionan
- [ ] `PATCH /roles/{id}` funciona
- [ ] `POST /roles/{id}/permissions` reemplaza permisos y audita
- [ ] `GET/POST /permissions/` funcionan
- [ ] Rol `ADMINISTRADOR` no restringible por API
- [ ] Códigos desconocidos devuelven `400`

#### Usuarios y sesiones

- [ ] `GET /users/{id}` con roles y permisos
- [ ] Reset de contraseña revoca sesiones
- [ ] Listado y revocación de sesiones por administrador
- [ ] Auto-bloqueo y auto-retiro de rol administrador bloqueados
- [ ] `UserUpdate.status` validado con `Literal`
- [ ] Errores `400/403/404/409/422` coherentes

#### Pruebas y calidad

- [ ] Tests unitarios RBAC/CSRF pasan
- [ ] Tests de integración pasan con PostgreSQL/Redis
- [ ] Suite completa sin fallos (136 previas + nuevas)
- [ ] Cobertura global `>= 75 %`
- [ ] `ruff check .` OK
- [ ] `ruff format --check .` OK
- [ ] `mypy src` OK
- [ ] Sin secretos ni contraseñas en el diff

#### Documentación

- [ ] `docs/api.md` actualizado
- [ ] `docs/roles-y-permisos.md` creado
- [ ] `docs/seguridad.md` actualizado
- [ ] `docs/pruebas.md` actualizado
- [ ] `README.md`/`docs/instalacion-desarrollo.md` con el seed RBAC
- [ ] ADR de CSRF registrada

---

## 23. Riesgos adicionales del cierre

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Desplegar sin ejecutar el seed RBAC | Alto: todo `/users` responde 403 | El seed forma parte del procedimiento de despliegue; verificar conteos tras aplicar |
| Clientes que no envían CSRF | Alto: POST bloqueados | Documentar `/auth/csrf`; actualizar frontend y tests antes de desplegar |
| Rotación de cookie CSRF tras login | Medio: headers desincronizados | El login reutiliza el token; no se rota |
| `ADMINISTRADOR` restringido por error | Alto: pérdida de acceso | API rechaza restringirlo; seed restaura el catálogo |
| Auto-bloqueo del único administrador | Alto: sistema inaccesible | Guardias en lock/update/roles; alta de respaldo con el script |
| Escalado por asignación de roles | Alto | `roles.manage` exclusivo del administrador; auditoría de cada cambio |
| Códigos de permiso inventados | Medio: RBAC inconsistente | Catálogo central en `permissions.py`/`seed_rbac.py`; tests de formato |
| Seed no idempotente | Medio: duplicados/errores en despliegue | Lock de asesoría, `select` previo y tests de idempotencia |
| `security_events` con datos sensibles | Alto | Solo identificadores y códigos; nunca tokens, hashes ni contraseñas |
| Tests de integración en paralelo | Medio: interferencias | Ejecutar con `-n 0` |

---

**NOTA FINAL:** Las secciones 1-15 describen el diseño original de B4. Las secciones 16-23
documentan el estado real y el bloque de cierre: seed RBAC, CSRF efectivo, endpoints de
roles/permisos, administración de sesiones, pruebas, documentación y validación. El núcleo
B4 ya está aplicado en el árbol de trabajo; el cierre descrito aquí debe implementarse y
validarse antes de declarar la fase terminada y hacer commit. No se ha hecho commit de este
bloque.
