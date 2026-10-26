# Fase B3 --- Configuración de la API y capa común

**Versión:** 1.0\
**Estado:** guía de implementación; base existente y cierre pendiente\
**Fecha:** 2026-10-26\
**Ámbito:** backend\
**Entrada:** B2 cerrada y verificada (41 tablas, Alembic, pruebas de integridad)\
**Salida:** aplicación FastAPI ejecutable, capa común de configuración,
errores, logging, middleware, salud, paginación, OpenAPI y pruebas de API

---

## 0. Cómo usar este documento

### 0.1 Regla de alcance

Este documento es una guía de implementación. No autoriza por sí mismo a
modificar código, ejecutar migraciones sobre bases compartidas, hacer commit ni
hacer push. La implementación se realiza cuando el usuario lo autorice.

Toda decisión de B3 debe respetar:

1. `docs/AGENTS.md`.
2. `docs/phases/GUIA_DESARROLLO_FASES_SGA.md`, fase B3.
3. `docs/phases/phaseB0_guide.md`, en especial configuración, logging,
   middleware, salud, app factory y pruebas.
4. `docs/phases/phaseB1_guide.md`, en especial contratos, convenciones de
   errores y OpenAPI preliminar.
5. `docs/phases/phaseB2_guide.md`, handoff a B3 y restricciones de persistencia.
6. Los ADR vigentes, principalmente ADR-0007 (observabilidad y errores),
   ADR-0002 (arquitectura modular) y ADR-0010 (configuración y secretos).

Si una instrucción de este documento contradice una regla de negocio de B1,
prevalece B1 y se detiene la implementación hasta resolver la contradicción.

### 0.2 Estado real de partida

B3 todavía figura como **Pendiente** en la guía maestra, aunque ya existe una
base técnica creada durante B0. Esta guía documenta el estado real, las brechas
y el código objetivo para cerrar la fase.

| Elemento | Estado real |
|---|---|
| `core/config.py` | Existe; configuración tipada y validaciones de producción |
| `core/errors.py` | Existe; sobre de error uniforme y manejadores |
| `core/logging.py` | Existe; structlog y redacción de claves sensibles de primer nivel |
| `core/middleware.py` | Existe; request-id; falta límite de cuerpo |
| `core/pagination.py` | Existe; página, tamaño y ordenamiento restringido |
| `core/runtime.py` | Existe; política de event loop en Windows |
| `core/security.py` | Existe; utilidades preparadas para B4, no autenticación B3 |
| `main.py` | Existe; app factory, lifespan, routers, CORS y hosts |
| `asgi.py` | Existe; instancia ASGI |
| `api/deps.py` | Existe; settings, base, Redis y sesión por petición |
| `api/v1/router.py` | Existe; router versionado |
| `api/v1/health.py` | Existe; liveness y readiness |
| `db/health.py` | Existe; comprobaciones de PostgreSQL y Redis |
| Pruebas unitarias | Configuración, salud de dependencias, paginación, seguridad, sesión |
| Pruebas de API | Errores, health, request-id y readiness sin dependencias |
| `phaseB3_guide.md` | Este documento |

### 0.3 Brechas que debe cerrar B3

1. Añadir un límite configurable de tamaño de cuerpo de petición y su respuesta
   `413` con el sobre de error uniforme.
2. Corregir el orden de middleware para que el `request_id` aparezca también en
   respuestas de CORS, `TrustedHost` y rechazos tempranos.
3. Ampliar la redacción de logs a estructuras anidadas y a claves de conexión.
4. Añadir pruebas de CORS, hosts no permitidos, OpenAPI habilitado/deshabilitado,
   cuerpo demasiado grande, redacción y readiness exitoso.
5. Documentar con precisión la política de filtros, ordenamiento estable,
   límites de paginación y protección de endpoints.
6. Ejecutar la suite completa, cobertura, Ruff, mypy, `alembic check` y
   `git diff --check` antes de declarar B3 completada.

### 0.4 Qué significa "sin omisiones" en B3

Incluye:

- árbol exacto de archivos;
- código completo de configuración, app factory, lifespan, routers, errores,
  logging, middleware, salud, paginación y dependencias;
- variables de entorno y validaciones de producción;
- orden de middleware y ciclo de una petición;
- formato de error y catálogo de códigos;
- contratos de paginación, ordenamiento y filtros;
- OpenAPI inicial y gating de documentación;
- límites de cuerpo, paginación y tiempos de espera;
- pruebas unitarias y de API;
- comandos PowerShell;
- smoke tests manuales;
- criterios verificables de terminado.

No incluye implementar autenticación, autorización, login, sesiones de usuario,
endpoints de negocio, repositorios, servicios de dominio, OCR, archivos,
búsqueda global, reportes ni frontend. Esas capas pertenecen a fases posteriores.

### 0.5 Principio de separación B0/B3/B4

- B0 dejó una base técnica ejecutable y una estructura modular.
- B3 convierte esa base en una capa HTTP común, segura y verificable.
- B4 implementa identidad, autenticación, sesiones y permisos.

B3 no debe inventar usuarios, credenciales, endpoints de dominio ni reglas de
negocio. Tampoco debe presentar como implementado un rate limiting que todavía
no existe.

---

## 1. Objetivo, alcance y entregables

### 1.1 Objetivo

Crear la infraestructura común de FastAPI para todos los módulos: configuración
validada, aplicación ejecutable, routers versionados, errores uniformes,
logging estructurado, request-id, CORS, hosts permitidos, health checks,
paginación, OpenAPI y límites básicos de petición.

### 1.2 Incluido

- Configuración tipada con `pydantic-settings` y validación al arranque.
- Separación entre desarrollo, pruebas, staging y producción.
- App factory inyectable para pruebas.
- Ciclo de vida con creación y cierre de PostgreSQL y Redis.
- Prefijo versionado `/api/v1`.
- Router raíz de salud.
- Dependencias comunes de settings, base de datos, Redis y sesión.
- Excepciones de aplicación y manejadores globales.
- Sobre JSON uniforme de error con `code`, `message`, `details` y `request_id`.
- Mapeo de códigos HTTP a códigos estables.
- Errores de validación sin reenviar los valores de entrada.
- Errores internos sin trazas ni detalles al cliente.
- Logging JSON en producción y consola legible en desarrollo.
- Redacción de contraseñas, tokens, cookies, secretos y cadenas de conexión.
- Middleware ASGI puro de request-id.
- Límite configurable de cuerpo de petición.
- CORS explícito con credenciales y sin comodines.
- `TrustedHostMiddleware` configurable.
- Documentación OpenAPI solo cuando esté habilitada.
- Liveness sin dependencias y readiness con PostgreSQL y Redis.
- Paginación `page`/`page_size`, ordenamiento restringido y contrato de filtros.
- Pruebas unitarias y de API de la capa común.

### 1.3 Fuera de alcance

- Login, logout, contraseñas, sesiones y CSRF funcional.
- Roles, permisos y autorización de endpoints.
- Rate limiting genérico o por credenciales.
- Endpoints CRUD de cajas, expedientes, tribunales o documentos.
- Búsqueda global, filtros de negocio y consultas SQL concretas.
- Carga y descarga de archivos.
- OCR, antivirus, tareas de importación y reportes.
- Frontend, tipos TypeScript y contratos de interfaz.
- Despliegue, TLS, proxy inverso y configuración de firewall.
- Migraciones de esquema; B2 ya las cubre.

El rate limiting de autenticación se implementará en B4; el de búsquedas
costosas en B8; el de archivos, OCR y exportaciones en B9, B10 y B14. B3 deja
los límites de cuerpo, paginación y tiempo que no dependen de identidad.

### 1.4 Entregables

| Entregable | Ubicación |
|---|---|
| Configuración | `backend/src/judicial_archive/core/config.py` |
| Errores | `backend/src/judicial_archive/core/errors.py` |
| Logging | `backend/src/judicial_archive/core/logging.py` |
| Middleware | `backend/src/judicial_archive/core/middleware.py` |
| Paginación | `backend/src/judicial_archive/core/pagination.py` |
| Runtime | `backend/src/judicial_archive/core/runtime.py` |
| App factory | `backend/src/judicial_archive/main.py` |
| ASGI | `backend/src/judicial_archive/asgi.py` |
| Dependencias | `backend/src/judicial_archive/api/deps.py` |
| Router v1 | `backend/src/judicial_archive/api/v1/router.py` |
| Salud API | `backend/src/judicial_archive/api/v1/health.py` |
| Salud de dependencias | `backend/src/judicial_archive/db/health.py` |
| Sesión de base | `backend/src/judicial_archive/db/session.py` |
| Helpers de prueba | `backend/tests/helpers.py` |
| Fixtures HTTP | `backend/tests/conftest.py` |
| Pruebas unitarias | `backend/tests/unit/` |
| Pruebas de API | `backend/tests/api/` |
| Documentación | este documento |

### 1.5 Criterios de aceptación

1. `uv run uvicorn judicial_archive.asgi:app --loop judicial_archive.core.runtime:selector_loop_factory` inicia con configuración válida.
2. Una configuración inválida falla al arrancar sin revelar secretos.
3. `GET /api/v1/health/live` responde `200` sin consultar dependencias.
4. `GET /api/v1/health/ready` responde `200` solo si PostgreSQL y Redis están
   disponibles; en caso contrario responde `503` sin revelar DSN ni trazas.
5. Toda respuesta HTTP incluye `X-Request-ID`, incluso errores tempranos de CORS
   o `TrustedHost`.
6. Un `request_id` entrante válido se conserva; uno inválido se reemplaza.
7. Los errores de aplicación, validación, HTTP y no controlados usan el mismo
   sobre JSON.
8. Los errores `500` no devuelven trazas, mensajes internos ni nombres de
   excepciones al cliente.
9. Los errores `422` no reenvían los valores enviados por el cliente.
10. CORS acepta solo orígenes configurados y rechaza comodines con credenciales.
11. Un host no permitido es rechazado con `400`.
12. `/docs`, `/redoc` y `/openapi.json` solo existen si `SGA_DOCS_ENABLED=true`.
13. OpenAPI incluye los endpoints reales de salud y sus modelos de respuesta.
14. Una petición que supera `SGA_MAX_REQUEST_BODY_BYTES` recibe `413` con el
    sobre de error y `X-Request-ID`.
15. La paginación limita `page_size` a 100 y el ordenamiento solo admite campos
    declarados por cada endpoint.
16. Los logs no contienen contraseñas, tokens, cookies, secretos ni DSN.
17. Ruff, formato, mypy y todas las pruebas pasan.
18. `alembic check` no detecta cambios de esquema.
19. No se añaden secretos, datos reales ni artefactos temporales al repositorio.
20. La documentación B3 queda validada en UTF-8 sin BOM, LF y sin espacios
    finales.

### 1.6 Definition of Done de B3

- [ ] Configuración y validaciones implementadas.
- [ ] App factory y lifespan verificados.
- [ ] Router `/api/v1` y health checks funcionando.
- [ ] Sobre de error y catálogo de códigos documentados.
- [ ] CORS, hosts, docs y límites probados.
- [ ] Request-id en todas las respuestas probado.
- [ ] Logs estructurados y redacción probados.
- [ ] Paginación y ordenamiento probados.
- [ ] OpenAPI probado.
- [ ] Pruebas unitarias y de API pasando.
- [ ] Suite completa y cobertura >= 75 %.
- [ ] Ruff, formato, mypy y `alembic check` sin errores.
- [ ] `git diff --check` sin salida.
- [ ] GUIA maestra actualizada solo cuando B3 esté realmente cerrada.

---

## 2. Prerrequisitos y estado de partida

### 2.1 Software

- Windows PowerShell 5.1 para los comandos de esta guía.
- Python 3.12 gestionado por `uv`.
- PostgreSQL 18 local con `sga_dev` y `sga_test`.
- Redis local para readiness completo y tareas futuras.
- `curl.exe` disponible en Windows para smoke tests.
- No se requiere Docker.

### 2.2 Estado comprobado

| Elemento | Estado |
|---|---|
| Último commit | `7d6aa4f chore(backend): Base de datos, modelos SQLAlchemy y migraciones Alembic` |
| B2 | Implementada, verificada y commiteada en `7d6aa4f` |
| B3 | Implementada y verificada; pendiente de commit |
| Suite actual | 130 pruebas pasando; cobertura 95,03 % |
| `FAIL_UNDER` | 75 |
| `SGA_*` | Prefijo único de configuración |
| Python | `>=3.12,<3.13` |
| FastAPI | `>=0.161,<1` |
| Pydantic | `>=2.14,<3` |
| Structlog | `>=26.1,<27` |
| PostgreSQL driver | psycopg 3 |
| Estado Git | Cambios B3 pendientes de revisión; no hacer commit sin autorización |

### 2.3 Comprobación inicial

```powershell
Set-Location C:\Users\Tony\Documents\sga
git status --short
git log --oneline -5
Set-Location backend
uv sync
uv run python -c "import fastapi, pydantic, structlog; print(fastapi.__version__, pydantic.__version__, structlog.__version__)"
```

Resultado esperado:

- dependencias sincronizadas;
- sin cambios ajenos sin revisar;
- FastAPI 0.161.x o superior compatible;
- Pydantic 2.14.x o superior;
- structlog 26.1.x o superior.

No continuar con una implementación si el repositorio contiene cambios ajenos
sin revisar.

### 2.4 Configuración local

El archivo `backend/.env` no se versiona. Debe contener, como mínimo:

```dotenv
SGA_ENVIRONMENT=development
SGA_DEBUG=true
SGA_SECRET_KEY=<clave-de-al-menos-32-caracteres>
SGA_DATABASE_URL=postgresql+psycopg://sga_dev:CONTRASENA@localhost:5432/sga_dev
SGA_REDIS_URL=redis://localhost:6379/0
SGA_DOCS_ENABLED=true
SGA_LOG_JSON=false
SGA_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
SGA_TRUSTED_HOSTS=localhost,127.0.0.1,testserver
```

Generar una clave local sin imprimirla en logs:

```powershell
Set-Location backend
uv run python -c "import secrets; print(secrets.token_urlsafe(64))"
```

### 2.5 Reglas de seguridad operativa

- No imprimir `SGA_DATABASE_URL`, `SGA_SECRET_KEY` ni `SGA_REDIS_URL`.
- No usar datos productivos en pruebas.
- No ejecutar integración en paralelo contra la misma base.
- No habilitar `/docs` en producción.
- No usar `SGA_CORS_ORIGINS=*` con credenciales.
- No añadir `testserver` a `SGA_TRUSTED_HOSTS` en producción.
- No registrar cuerpos de petición, cabeceras de autorización ni documentos.
- No declarar una prueba como ejecutada si no se ejecutó.

---

## 3. Arquitectura de la capa común

### 3.1 Capas

```text
Petición HTTP
    |
    v
RequestContextMiddleware      request-id, contextvars, cabecera de respuesta
    |
    v
CORSMiddleware                origen, credenciales, preflight
    |
    v
TrustedHostMiddleware         Host permitido
    |
    v
RequestBodyLimitMiddleware    Content-Length y límite de cuerpo
    |
    v
Starlette ExceptionMiddleware manejadores de errores
    |
    v
Router /api/v1                health y futuros módulos
    |
    v
Dependencias                  settings, Database, Redis, AsyncSession
    |
    v
Servicios de dominio          fases posteriores
```

### 3.2 Orden de middleware

El orden exterior debe ser:

1. `RequestContextMiddleware` --- el más externo.
2. `CORSMiddleware`.
3. `TrustedHostMiddleware`.
4. `RequestBodyLimitMiddleware` --- el más interno de los middleware propios.

Motivo:

- El request-id debe existir incluso si CORS rechaza un origen, si el host no es
  permitido o si el cuerpo excede el límite.
- CORS debe envolver a `TrustedHost` y al límite de cuerpo para que sus
  respuestas de error reciban las cabeceras CORS cuando corresponda.
- El límite de cuerpo debe ejecutarse antes de leer el cuerpo y después de las
  comprobaciones de origen y host.

En Starlette, el último middleware agregado es el más externo. Por eso el orden
de llamadas a `add_middleware` es el inverso:

```python
app.add_middleware(RequestBodyLimitMiddleware, max_bytes=...)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=...)
app.add_middleware(CORSMiddleware, ...)
app.add_middleware(RequestContextMiddleware, header_name=...)
```

La base B0 agregaba `RequestContextMiddleware` primero y CORS al final. Eso
deja el request-id por dentro de CORS y `TrustedHost`. B3 debe corregirlo para
cumplir ADR-0007 en todas las respuestas.

### 3.3 Ciclo de vida

1. `asgi.py` importa `create_app`.
2. `create_app` resuelve y valida `Settings`.
3. Se configura logging.
4. Se crea `FastAPI` con documentación condicionada.
5. Se registran manejadores de excepciones.
6. Se incluye el router `/api/v1`.
7. Se agregan middleware en el orden documentado.
8. Al arrancar, `lifespan` crea `Database` y `Redis`, y los publica en
   `app.state`.
9. Al apagar, cierra Redis y libera el engine de PostgreSQL.

No se conecta a PostgreSQL ni Redis durante la construcción de la app: la
conexión se valida en readiness y en la primera operación real. Esto permite
crear la app en pruebas sin infraestructura.

### 3.4 Inyección y pruebas

- `create_app(settings, configure_logs=False)` permite probar con settings
  explícitos y sin reconfigurar el logging global.
- `build_test_settings` centraliza valores seguros de prueba.
- `ASGITransport` de httpx permite probar la app sin abrir un puerto.
- Los tests de dependencias usan dobles mínimos para PostgreSQL y Redis.
- No se usan bases productivas ni credenciales reales.

### 3.5 Reglas de diseño

- La capa común no contiene reglas de negocio.
- Los errores de dominio se expresan mediante subclases de `AppError`.
- Los endpoints no construyen respuestas de error a mano.
- Los endpoints no capturan excepciones para ocultarlas.
- Los logs no incluyen datos personales innecesarios.
- Los secretos nunca forman parte de una respuesta.
- OpenAPI se deriva del código, no se escribe a mano.
- Los límites tienen valores por defecto seguros y configurables.

---

## 4. Árbol exacto de archivos

```text
backend/
├── .env.example
├── pyproject.toml
├── src/
│   └── judicial_archive/
│       ├── __init__.py
│       ├── asgi.py
│       ├── main.py
│       ├── api/
│       │   ├── __init__.py
│       │   ├── deps.py
│       │   └── v1/
│       │       ├── __init__.py
│       │       ├── health.py
│       │       └── router.py
│       ├── core/
│       │   ├── __init__.py
│       │   ├── config.py
│       │   ├── errors.py
│       │   ├── logging.py
│       │   ├── middleware.py
│       │   ├── pagination.py
│       │   ├── runtime.py
│       │   └── security.py
│       └── db/
│           ├── __init__.py
│           ├── health.py
│           └── session.py
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── helpers.py
    ├── api/
    │   ├── __init__.py
    │   ├── test_errors.py
    │   ├── test_health.py
    │   ├── test_middleware.py
    │   └── test_openapi.py
    └── unit/
        ├── __init__.py
        ├── test_config.py
        ├── test_db_health.py
        ├── test_logging.py
        ├── test_pagination.py
        ├── test_security.py
        └── test_session.py
```

No crear módulos de negocio vacíos. Los archivos `test_middleware.py` y
`test_openapi.py` son nuevos y pertenecen a B3. `test_logging.py` también es
nuevo.

---

## 5. Configuración: `core/config.py`

### 5.1 Responsabilidad

- Leer variables con prefijo `SGA_`.
- Validar tipos, URLs, tamaños y listas.
- Rechazar configuraciones inseguras en producción.
- Cachear la configuración por proceso.
- No registrar ni serializar secretos.

### 5.2 Código objetivo

Archivo: `backend/src/judicial_archive/core/config.py`

```python
from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import (
    Field,
    PostgresDsn,
    RedisDsn,
    SecretStr,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Environment(StrEnum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
StorageBackend = Literal["local"]


class Settings(BaseSettings):
    """Configuracion tipada de la aplicacion, validada al arrancar."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="SGA_",
        case_sensitive=False,
        extra="forbid",
        validate_default=True,
    )

    secret_key: SecretStr
    database_url: PostgresDsn
    redis_url: RedisDsn

    app_name: str = "SGA - Sistema de Gestion Documental Judicial"
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    docs_enabled: bool = False
    log_level: LogLevel = "INFO"
    log_json: bool = True

    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)
    trusted_hosts: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["localhost", "127.0.0.1", "testserver"]
    )
    request_id_header: str = Field(
        default="X-Request-ID",
        pattern=r"^[A-Za-z0-9-]{3,64}$",
    )
    max_request_body_bytes: int = Field(default=1_048_576, ge=1024, le=16_777_216)

    db_pool_size: int = Field(default=10, ge=1, le=100)
    db_max_overflow: int = Field(default=20, ge=0, le=100)
    db_echo: bool = False
    db_pool_pre_ping: bool = True
    db_pool_recycle_seconds: int = Field(default=1800, ge=60, le=86400)

    redis_socket_timeout_seconds: float = Field(default=3.0, gt=0, le=60)

    session_cookie_name: str = "sga_session"
    session_cookie_secure: bool = True
    session_idle_minutes: int = Field(default=30, ge=5, le=1440)
    session_absolute_hours: int = Field(default=12, ge=1, le=720)
    csrf_cookie_name: str = "sga_csrf"
    csrf_header_name: str = "X-CSRF-Token"

    task_queue_name: str = "sga"
    task_max_jobs: int = Field(default=4, ge=1, le=64)
    task_job_timeout_seconds: int = Field(default=900, ge=10, le=86400)

    storage_backend: StorageBackend = "local"
    storage_root: Path = Path("var/storage")

    readiness_timeout_seconds: float = Field(default=3.0, gt=0, le=30)

    @field_validator("secret_key")
    @classmethod
    def _validate_secret_key(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < 32:
            msg = "SGA_SECRET_KEY debe tener al menos 32 caracteres."
            raise ValueError(msg)
        return value

    @field_validator("api_v1_prefix")
    @classmethod
    def _validate_api_prefix(cls, value: str) -> str:
        if not value.startswith("/") or value.endswith("/"):
            msg = "SGA_API_V1_PREFIX debe comenzar con '/' y no terminar con '/'."
            raise ValueError(msg)
        return value

    @field_validator("cors_origins", "trusted_hosts", mode="before")
    @classmethod
    def _split_comma_separated(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("cors_origins")
    @classmethod
    def _validate_cors_origins(cls, origins: list[str]) -> list[str]:
        for origin in origins:
            if origin == "*":
                continue
            if not origin.startswith(("http://", "https://")):
                msg = f"Origen CORS invalido: {origin!r}; debe incluir esquema."
                raise ValueError(msg)
            if origin.endswith("/"):
                msg = f"Origen CORS invalido: {origin!r}; no debe terminar en '/'."
                raise ValueError(msg)
        return origins

    @model_validator(mode="after")
    def _validate_cors_credentials(self) -> Self:
        if any(origin.strip() == "*" for origin in self.cors_origins):
            msg = "SGA_CORS_ORIGINS no puede contener '*' porque se usan credenciales"
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def _validate_production_rules(self) -> Self:
        if self.environment is not Environment.PRODUCTION:
            return self

        problems: list[str] = []
        if self.debug:
            problems.append("SGA_DEBUG debe ser false en produccion")
        if self.docs_enabled:
            problems.append("SGA_DOCS_ENABLED debe ser false en produccion")
        if not self.log_json:
            problems.append("SGA_LOG_JSON debe ser true en produccion")
        if not self.session_cookie_secure:
            problems.append("SGA_SESSION_COOKIE_SECURE debe ser true en produccion")
        if "testserver" in self.trusted_hosts:
            problems.append(
                "SGA_TRUSTED_HOSTS no puede contener 'testserver' en produccion"
            )
        if "*" in self.trusted_hosts:
            problems.append("SGA_TRUSTED_HOSTS no puede contener '*' en produccion")

        if problems:
            msg = "Configuracion de produccion invalida: " + "; ".join(problems)
            raise ValueError(msg)
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Devuelve la configuracion validada, cacheada por proceso."""
    return Settings()  # pyright: ignore[reportCallIssue]
```

### 5.3 Variables de entorno

| Variable | Tipo | Defecto | Uso |
|---|---|---|---|
| `SGA_ENVIRONMENT` | enum | `development` | Reglas por entorno |
| `SGA_DEBUG` | bool | `false` | Debug controlado |
| `SGA_SECRET_KEY` | secreto | obligatorio | Firma futura de sesiones |
| `SGA_DATABASE_URL` | DSN PostgreSQL | obligatorio | Base de datos |
| `SGA_REDIS_URL` | DSN Redis | obligatorio | Redis |
| `SGA_API_V1_PREFIX` | str | `/api/v1` | Prefijo versionado |
| `SGA_DOCS_ENABLED` | bool | `false` | Swagger/OpenAPI |
| `SGA_LOG_LEVEL` | enum | `INFO` | Nivel mínimo |
| `SGA_LOG_JSON` | bool | `true` | JSON en producción |
| `SGA_CORS_ORIGINS` | lista CSV | vacía | Orígenes permitidos |
| `SGA_TRUSTED_HOSTS` | lista CSV | local/test | Hosts permitidos |
| `SGA_REQUEST_ID_HEADER` | str | `X-Request-ID` | Cabecera de correlación |
| `SGA_MAX_REQUEST_BODY_BYTES` | int | `1048576` | Límite de cuerpo |
| `SGA_DB_POOL_SIZE` | int | `10` | Pool PostgreSQL |
| `SGA_DB_MAX_OVERFLOW` | int | `20` | Pool PostgreSQL |
| `SGA_DB_POOL_PRE_PING` | bool | `true` | Reciclado de conexiones |
| `SGA_READINESS_TIMEOUT_SECONDS` | float | `3.0` | Timeout de readiness |
| `SGA_STORAGE_ROOT` | ruta | `var/storage` | Almacenamiento futuro |

### 5.4 Reglas de producción

La aplicación no debe arrancar en producción si:

- `SGA_DEBUG=true`;
- `SGA_DOCS_ENABLED=true`;
- `SGA_LOG_JSON=false`;
- `SGA_SESSION_COOKIE_SECURE=false`;
- `SGA_TRUSTED_HOSTS` contiene `testserver`;
- `SGA_TRUSTED_HOSTS` contiene `*`;
- `SGA_CORS_ORIGINS` contiene `*`;
- la clave secreta tiene menos de 32 caracteres.

Los errores de validación de Pydantic no deben incluir el valor de
`secret_key` ni la contraseña del DSN en la salida de arranque. No imprimir
`Settings` completo. `get_settings()` captura `ValidationError` y lanza un
`RuntimeError` con solo campo y mensaje, usando `from None` para no encadenar la
excepción original con los valores de entrada.

### 5.5 Pruebas asociadas

- configuración válida;
- clave corta rechazada;
- prefijo sin `/` inicial rechazado;
- prefijo con `/` final rechazado;
- listas separadas por coma;
- producción segura aceptada;
- cada configuración insegura de producción rechazada;
- origen CORS con esquema inválido rechazado;
- origen CORS con `/` final rechazado;
- tamaño de cuerpo fuera de rango rechazado;
- error de arranque sin secreto ni contraseña del DSN.

---

## 6. Runtime y aplicación

### 6.1 `core/runtime.py`

Archivo: `backend/src/judicial_archive/core/runtime.py`

```python
from __future__ import annotations

import asyncio
import os


def configure_event_loop_policy() -> None:
    """Usa SelectorEventLoop en Windows para compatibilidad con psycopg async."""
    if os.name != "nt":
        return

    policy_type = getattr(asyncio, "WindowsSelectorEventLoopPolicy", None)
    if policy_type is not None:
        asyncio.set_event_loop_policy(  # pyright: ignore[reportDeprecated]
            policy_type()
        )


def selector_loop_factory() -> asyncio.AbstractEventLoop:
    """Fabrica de loop para uvicorn en Windows; psycopg no usa Proactor."""
    return asyncio.SelectorEventLoop()
```

Debe ejecutarse antes de crear el engine de SQLAlchemy. En `main.py` se llama a
nivel de módulo, antes de `create_app`.

### 6.2 `main.py`

Archivo: `backend/src/judicial_archive/main.py`

```python
from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import cast

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from judicial_archive import __version__
from judicial_archive.api.v1.router import api_router
from judicial_archive.core.config import Environment, Settings, get_settings
from judicial_archive.core.errors import register_exception_handlers
from judicial_archive.core.logging import configure_logging
from judicial_archive.core.middleware import (
    RequestBodyLimitMiddleware,
    RequestContextMiddleware,
    TrustedHostMiddleware,
)
from judicial_archive.core.runtime import configure_event_loop_policy
from judicial_archive.db.session import Database

configure_event_loop_policy()

logger = structlog.get_logger(__name__)

_OPENAPI_TAGS = [
    {
        "name": "Salud",
        "description": "Disponibilidad del proceso y de sus dependencias.",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    settings = cast(Settings, app.state.settings)
    database = Database(settings)
    redis: Redis = Redis.from_url(  # pyright: ignore[reportUnknownMemberType]
        str(settings.redis_url),
        encoding="utf-8",
        decode_responses=True,
        socket_connect_timeout=settings.redis_socket_timeout_seconds,
        socket_timeout=settings.redis_socket_timeout_seconds,
    )
    app.state.database = database
    app.state.redis = redis

    logger.info(
        "application_starting",
        environment=settings.environment.value,
        version=__version__,
    )
    try:
        yield
    finally:
        await redis.aclose()
        await database.dispose()
        logger.info("application_stopped")


def create_app(
    settings: Settings | None = None, *, configure_logs: bool = True
) -> FastAPI:
    resolved_settings = settings or get_settings()
    if configure_logs:
        configure_logging(resolved_settings)

    docs_enabled = resolved_settings.docs_enabled
    app = FastAPI(
        title=resolved_settings.app_name,
        description="API del Sistema de Gestion Documental Judicial.",
        version=__version__,
        debug=(
            resolved_settings.debug
            and resolved_settings.environment is Environment.DEVELOPMENT
        ),
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
        openapi_tags=_OPENAPI_TAGS,
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings

    register_exception_handlers(app)
    app.include_router(api_router, prefix=resolved_settings.api_v1_prefix)

    # El ultimo middleware agregado es el mas externo.
    app.add_middleware(
        RequestBodyLimitMiddleware,
        max_bytes=resolved_settings.max_request_body_bytes,
    )
    if resolved_settings.trusted_hosts:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=resolved_settings.trusted_hosts,
        )
    if resolved_settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=resolved_settings.cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=[
                "Authorization",
                "Content-Type",
                resolved_settings.csrf_header_name,
                resolved_settings.request_id_header,
            ],
            expose_headers=[resolved_settings.request_id_header],
            max_age=600,
        )
    app.add_middleware(
        RequestContextMiddleware,
        header_name=resolved_settings.request_id_header,
    )

    return app
```

### 6.3 `asgi.py`

Archivo: `backend/src/judicial_archive/asgi.py`

```python
from __future__ import annotations

from judicial_archive.main import create_app

app = create_app()
```

Uso local:

```powershell
Set-Location backend
uv run uvicorn judicial_archive.asgi:app --reload --host 127.0.0.1 --port 8000 --loop judicial_archive.core.runtime:selector_loop_factory
```

En Windows el loop Selector es obligatorio para psycopg async. Uvicorn 0.54
crea el loop antes de importar la app, por lo que cambiar la política dentro de
`main.py` no basta; se debe indicar la fábrica con `--loop`.

### 6.4 `api/deps.py`

Archivo: `backend/src/judicial_archive/api/deps.py`

```python
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import cast

from fastapi import Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.core.config import Settings
from judicial_archive.db.session import Database


def get_app_settings(request: Request) -> Settings:
    """Devuelve la configuracion validada de la aplicacion."""
    return cast(Settings, request.app.state.settings)


def get_database(request: Request) -> Database:
    """Devuelve el contenedor del engine y las sesiones."""
    return cast(Database, request.app.state.database)


def get_redis(request: Request) -> Redis:
    """Devuelve el cliente Redis compartido del proceso."""
    return cast(Redis, request.app.state.redis)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Entrega una sesion por peticion; el servicio decide commit o rollback."""
    database = get_database(request)
    async with database.session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
```

La sesión no hace `commit` automático. Los servicios de fases posteriores deben
delimitar la transacción y confirmar solo cuando la operación completa sea
válida.

### 6.5 `db/session.py`

Archivo: `backend/src/judicial_archive/db/session.py`

```python
from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from judicial_archive.core.config import Settings


class Database:
    """Contenedor del motor y la fabrica de sesiones asincronas."""

    def __init__(self, settings: Settings) -> None:
        self._engine: AsyncEngine = create_async_engine(
            str(settings.database_url),
            echo=settings.db_echo,
            pool_pre_ping=settings.db_pool_pre_ping,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_recycle=settings.db_pool_recycle_seconds,
        )
        self._session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

    @property
    def engine(self) -> AsyncEngine:
        return self._engine

    def session(self) -> AsyncSession:
        return self._session_factory()

    async def dispose(self) -> None:
        await self._engine.dispose()
```

---

## 7. Logging estructurado: `core/logging.py`

### 7.1 Responsabilidad

- Configurar structlog y el logging estándar una sola vez.
- Emitir JSON en producción y consola legible en desarrollo.
- Propagar `request_id` desde contextvars.
- Redactar claves sensibles incluso dentro de diccionarios anidados.
- Evitar que logs de uvicorn dupliquen handlers.

### 7.2 Código objetivo

Archivo: `backend/src/judicial_archive/core/logging.py`

```python
from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor

from judicial_archive.core.config import Settings

_SENSITIVE_KEY_MARKERS = frozenset(
    {
        "password",
        "passwd",
        "secret",
        "token",
        "authorization",
        "cookie",
        "api_key",
        "apikey",
        "session",
        "dsn",
        "database_url",
        "redis_url",
        "connection_string",
    }
)


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(marker in lowered for marker in _SENSITIVE_KEY_MARKERS)


def _redact_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "***" if _is_sensitive_key(str(key)) else _redact_value(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact_value(item) for item in value)
    return value


def _redact_sensitive_values(
    _logger: Any,
    _method_name: str,
    event_dict: EventDict,
) -> EventDict:
    """Reemplaza valores sensibles antes de emitir el log."""
    for key in list(event_dict):
        event_dict[key] = (
            "***" if _is_sensitive_key(key) else _redact_value(event_dict[key])
        )
    return event_dict


def _shared_processors() -> list[Processor]:
    return [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        _redact_sensitive_values,
    ]


def configure_logging(settings: Settings) -> None:
    """Configura structlog y el logging estandar de forma unificada."""
    shared_processors = _shared_processors()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    renderer: Processor
    if settings.log_json:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=renderer,
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(settings.log_level)

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uv_logger = logging.getLogger(logger_name)
        uv_logger.handlers.clear()
        uv_logger.propagate = True
```

### 7.3 Convenciones de eventos

- Nombres de evento en `snake_case`.
- Campos en inglés técnico consistente.
- No incluir cuerpos de petición, documentos ni valores de formulario.
- No incluir `password`, `token`, `cookie`, `authorization` ni DSN.
- Usar `request_id` para correlacionar.
- Usar `error_type` para el tipo de excepción, no el mensaje interno.
- Los 5xx se registran con traza en servidor; el cliente recibe mensaje genérico.
- Los 4xx esperados se registran como advertencia, no como error crítico.

Ejemplo de evento JSON en producción:

```json
{
  "event": "application_error",
  "status_code": 404,
  "error_code": "not_found",
  "path": "/api/v1/boxes/00000000-0000-0000-0000-000000000000",
  "method": "GET",
  "request_id": "5f0f0e8c9a4b4f0e8f0a9b8c7d6e5f4a",
  "timestamp": "2026-10-26T12:00:00.000000Z",
  "level": "warning",
  "logger": "judicial_archive.core.errors"
}
```

### 7.4 Límites de la redacción

La redacción por clave no puede limpiar un secreto incluido dentro del texto
libre de `event` o `message`. Regla obligatoria: no pasar secretos como parte
del mensaje. Si una excepción de terceros incluye una URL con contraseña, no
registrar `str(exc)`; registrar solo `type(exc).__name__`.

### 7.5 Pruebas asociadas

- redacción de una clave sensible de primer nivel;
- redacción recursiva en diccionarios anidados;
- redacción en listas y tuplas;
- conservación de claves no sensibles;
- redacción de `database_url`, `redis_url` y `dsn`;
- configuración de logging sin duplicar handlers de uvicorn.

---

## 8. Request-id y límite de cuerpo: `core/middleware.py`

### 8.1 Request-id

- Cabecera por defecto: `X-Request-ID`.
- Un valor entrante se conserva solo si cumple `^[A-Za-z0-9._-]{8,64}$`.
- Si falta o no es válido, se genera `uuid4().hex` (32 caracteres).
- Se guarda en `request.state.request_id` y en contextvars de structlog.
- Se devuelve en la cabecera de respuesta.
- Se limpia al finalizar para no contaminar la siguiente petición.
- No se confía en el valor para autorización ni para identidad.
- No se registra como dato sensible.

### 8.2 Límite de cuerpo

- Límite por defecto: 1 MiB.
- Se comprueba `Content-Length` antes de entregar la petición a la app.
- Si el valor declarado supera el límite, se responde `413` con el sobre común.
- Si `Content-Length` es inválido o negativo, se responde `400`.
- Las rutas exentas se pueden declarar para futuras cargas controladas, pero B3
  no exime ninguna.
- Un cuerpo `chunked` sin `Content-Length` no se limita en este middleware; el
  proxy inverso y el servidor deben imponer un límite duro. Esta limitación se
  documenta y se corrige en B9 para cargas de archivos.
- No se lee ni se registra el cuerpo para decidir.

### 8.3 Código objetivo

Archivo: `backend/src/judicial_archive/core/middleware.py`

```python
from __future__ import annotations

import re
from uuid import uuid4

import structlog
from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from judicial_archive.core.errors import ErrorCode, build_error_response

_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{8,64}$")


class RequestContextMiddleware:
    """Middleware ASGI puro que asigna y propaga un request-id seguro."""

    def __init__(self, app: ASGIApp, *, header_name: str = "X-Request-ID") -> None:
        self.app = app
        self.header_name = header_name

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        incoming = headers.get(self.header_name)
        request_id = (
            incoming
            if incoming and _REQUEST_ID_PATTERN.fullmatch(incoming)
            else uuid4().hex
        )

        state = scope.setdefault("state", {})
        state["request_id"] = request_id

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        async def send_wrapped(message: Message) -> None:
            if message["type"] == "http.response.start":
                response_headers = MutableHeaders(scope=message)
                response_headers[self.header_name] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_wrapped)
        finally:
            structlog.contextvars.clear_contextvars()


class RequestBodyLimitMiddleware:
    """Rechaza peticiones cuya longitud declarada supera el limite."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        max_bytes: int,
        exempt_path_prefixes: tuple[str, ...] = (),
    ) -> None:
        self.app = app
        self.max_bytes = max_bytes
        self.exempt_path_prefixes = exempt_path_prefixes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = str(scope.get("path", ""))
        if any(path.startswith(prefix) for prefix in self.exempt_path_prefixes):
            await self.app(scope, receive, send)
            return

        content_length = Headers(scope=scope).get("content-length")
        if content_length is None:
            await self.app(scope, receive, send)
            return

        try:
            declared = int(content_length)
        except ValueError:
            await self._reject(
                scope,
                receive,
                send,
                status_code=400,
                code=ErrorCode.BAD_REQUEST,
                message="El encabezado Content-Length no es valido.",
            )
            return

        if declared < 0:
            await self._reject(
                scope,
                receive,
                send,
                status_code=400,
                code=ErrorCode.BAD_REQUEST,
                message="El encabezado Content-Length no es valido.",
            )
            return

        if declared > self.max_bytes:
            await self._reject(
                scope,
                receive,
                send,
                status_code=413,
                code=ErrorCode.PAYLOAD_TOO_LARGE,
                message="La peticion excede el tamano permitido.",
                details={"max_bytes": self.max_bytes},
            )
            return

        await self.app(scope, receive, send)

    async def _reject(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
        *,
        status_code: int,
        code: ErrorCode,
        message: str,
        details: dict[str, object] | None = None,
    ) -> None:
        state = scope.get("state")
        request_id = state.get("request_id") if isinstance(state, dict) else None
        response: Response = build_error_response(
            status_code=status_code,
            code=code,
            message=message,
            request_id=request_id if isinstance(request_id, str) else None,
            details=details,
        )
        await response(scope, receive, send)
```

### 8.4 Pruebas asociadas

- request-id válido conservado;
- request-id ausente genera 32 caracteres;
- request-id con `<script>` se reemplaza;
- request-id presente en respuestas `200`, `404`, `413`, CORS y host inválido;
- cuerpo mayor al límite devuelve `413`;
- `Content-Length` inválido devuelve `400`;
- cuerpo dentro del límite llega al endpoint;
- ruta exenta no se bloquea, si se configura en una fase futura.

---

## 9. Errores uniformes: `core/errors.py`

### 9.1 Sobre de error

Todas las respuestas de error usan:

```json
{
  "error": {
    "code": "not_found",
    "message": "La caja solicitada no existe.",
    "details": null,
    "request_id": "5f0f0e8c9a4b4f0e8f0a9b8c7d6e5f4a"
  }
}
```

Reglas:

- `code` es estable y apto para lógica de cliente.
- `message` es legible y en español.
- `details` es opcional y no contiene secretos.
- `request_id` permite correlación.
- Nunca se devuelve `traceback`, `type` de excepción interna, SQL ni DSN.
- Los errores de validación no incluyen `input` ni `ctx` con valores enviados.
- Los errores `500` usan un mensaje genérico.

### 9.2 Catálogo de códigos

| Código | HTTP | Uso |
|---|---|---|
| `validation_error` | 422 | Parámetros o cuerpo inválidos |
| `bad_request` | 400 | Petición mal formada |
| `unauthorized` | 401 | Falta autenticación; se usa en B4 |
| `forbidden` | 403 | Permiso insuficiente; se usa en B4 |
| `not_found` | 404 | Recurso inexistente |
| `method_not_allowed` | 405 | Método no permitido |
| `conflict` | 409 | Conflicto de estado o unicidad |
| `payload_too_large` | 413 | Cuerpo mayor al límite |
| `rate_limited` | 429 | Límite de tasa; se activa en B4/B8 |
| `service_unavailable` | 503 | Dependencia no disponible |
| `internal_error` | 500 | Error no controlado |

Los códigos de negocio específicos se agregan en fases posteriores sin romper el
sobre. Ejemplos futuros: `invalid_credentials`, `position_occupied`,
`loan_not_open`, `import_not_approved`. No se inventan en B3.

### 9.3 Código objetivo

Archivo: `backend/src/judicial_archive/core/errors.py`

```python
from __future__ import annotations

from enum import StrEnum
from typing import Any, cast

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException


class ErrorCode(StrEnum):
    VALIDATION_ERROR = "validation_error"
    BAD_REQUEST = "bad_request"
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    NOT_FOUND = "not_found"
    METHOD_NOT_ALLOWED = "method_not_allowed"
    CONFLICT = "conflict"
    PAYLOAD_TOO_LARGE = "payload_too_large"
    RATE_LIMITED = "rate_limited"
    SERVICE_UNAVAILABLE = "service_unavailable"
    INTERNAL_ERROR = "internal_error"


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None
    request_id: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


class AppError(Exception):
    """Error de aplicacion con codigo estable y estado HTTP asociado."""

    status_code: int = 400
    code: ErrorCode = ErrorCode.BAD_REQUEST

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class UnauthorizedError(AppError):
    status_code = 401
    code = ErrorCode.UNAUTHORIZED


class ForbiddenError(AppError):
    status_code = 403
    code = ErrorCode.FORBIDDEN


class NotFoundError(AppError):
    status_code = 404
    code = ErrorCode.NOT_FOUND


class ConflictError(AppError):
    status_code = 409
    code = ErrorCode.CONFLICT


class InvalidParameterError(AppError):
    status_code = 422
    code = ErrorCode.VALIDATION_ERROR


class PayloadTooLargeError(AppError):
    status_code = 413
    code = ErrorCode.PAYLOAD_TOO_LARGE


class RateLimitedError(AppError):
    status_code = 429
    code = ErrorCode.RATE_LIMITED


class ServiceUnavailableError(AppError):
    status_code = 503
    code = ErrorCode.SERVICE_UNAVAILABLE


class InternalError(AppError):
    status_code = 500
    code = ErrorCode.INTERNAL_ERROR


logger = structlog.get_logger(__name__)

_HTTP_STATUS_TO_CODE: dict[int, ErrorCode] = {
    400: ErrorCode.BAD_REQUEST,
    401: ErrorCode.UNAUTHORIZED,
    403: ErrorCode.FORBIDDEN,
    404: ErrorCode.NOT_FOUND,
    405: ErrorCode.METHOD_NOT_ALLOWED,
    409: ErrorCode.CONFLICT,
    413: ErrorCode.PAYLOAD_TOO_LARGE,
    422: ErrorCode.VALIDATION_ERROR,
    429: ErrorCode.RATE_LIMITED,
    503: ErrorCode.SERVICE_UNAVAILABLE,
}


def _request_id(request: Request) -> str | None:
    value = getattr(request.state, "request_id", None)
    return value if isinstance(value, str) else None


def build_error_response(
    *,
    status_code: int,
    code: ErrorCode,
    message: str,
    request_id: str | None,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    payload = ErrorResponse(
        error=ErrorDetail(
            code=code.value,
            message=message,
            details=details,
            request_id=request_id,
        )
    ).model_dump(mode="json")
    return JSONResponse(status_code=status_code, content=payload)


def _serialize_validation_errors(exc: RequestValidationError) -> list[dict[str, Any]]:
    serialized: list[dict[str, Any]] = []
    for error in exc.errors():
        serialized.append(
            {
                "location": list(error.get("loc", ())),
                "message": error.get("msg", "Valor invalido."),
                "type": error.get("type", "value_error"),
            }
        )
    return serialized


async def app_error_handler(request: Request, exc: Exception) -> Response:
    app_error = cast(AppError, exc)
    log_method = logger.error if app_error.status_code >= 500 else logger.warning
    log_method(
        "application_error",
        status_code=app_error.status_code,
        error_code=app_error.code.value,
        path=request.url.path,
        method=request.method,
        exc_info=app_error if app_error.status_code >= 500 else None,
    )
    return build_error_response(
        status_code=app_error.status_code,
        code=app_error.code,
        message=app_error.message,
        request_id=_request_id(request),
        details=app_error.details,
    )


async def validation_exception_handler(request: Request, exc: Exception) -> Response:
    validation_error = cast(RequestValidationError, exc)
    return build_error_response(
        status_code=422,
        code=ErrorCode.VALIDATION_ERROR,
        message="Los datos enviados no son validos.",
        request_id=_request_id(request),
        details={"errors": _serialize_validation_errors(validation_error)},
    )


async def http_exception_handler(request: Request, exc: Exception) -> Response:
    http_error = cast(StarletteHTTPException, exc)
    detail = cast(object, http_error.detail)
    if http_error.status_code >= 500:
        message = "Error interno del servidor."
    elif isinstance(detail, str):
        message = detail
    else:
        message = "Error en la solicitud."
    default_code = (
        ErrorCode.INTERNAL_ERROR
        if http_error.status_code >= 500
        else ErrorCode.BAD_REQUEST
    )
    code = _HTTP_STATUS_TO_CODE.get(http_error.status_code, default_code)
    return build_error_response(
        status_code=http_error.status_code,
        code=code,
        message=message,
        request_id=_request_id(request),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> Response:
    logger.error(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
        error_type=type(exc).__name__,
        exc_info=exc,
    )
    return build_error_response(
        status_code=500,
        code=ErrorCode.INTERNAL_ERROR,
        message="Error interno del servidor.",
        request_id=_request_id(request),
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
```

### 9.4 Reglas de uso

- Un endpoint lanza `NotFoundError`, `ConflictError`, `InvalidParameterError` o
  la subclase que corresponda.
- No se lanza `HTTPException` para errores de negocio si existe un `AppError`.
- No se construye un `JSONResponse` de error dentro de un endpoint.
- No se captura `Exception` para devolver un mensaje inventado.
- Si se agrega un código, se actualiza el catálogo, el mapeo HTTP y las pruebas.
- Los detalles deben ser útiles para el cliente y seguros para el servidor.
- No se expone el nombre de la tabla, columna, restricción o consulta SQL.

### 9.5 Pruebas asociadas

- `AppError` usa el sobre y conserva el request-id.
- `NotFoundError` devuelve `404` y `not_found`.
- Error de validación devuelve `422` y no reenvía el valor.
- Error no controlado devuelve `500` genérico.
- `HTTPException` 404 y 405 se mapean correctamente.
- `PayloadTooLargeError` devuelve `413`.
- Un `ValueError` no controlado no expone su mensaje.

---

## 10. CORS, hosts y documentación

### 10.1 CORS

Configuración obligatoria:

- `allow_origins` solo con orígenes explícitos.
- `allow_credentials=True`.
- Sin `*` en orígenes cuando hay credenciales.
- Métodos explícitos.
- Cabeceras permitidas: `Authorization`, `Content-Type`, CSRF y request-id.
- `expose_headers` incluye request-id.
- `max_age=600`.

No usar `allow_origins=["*"]`. No confiar en CORS como autenticación. CORS no
protege endpoints; solo controla qué orígenes del navegador pueden leer
respuestas.

### 10.2 TrustedHost

`TrustedHostMiddleware` rechaza un `Host` no permitido con `400`. En producción
debe contener solo dominios reales, sin `*` y sin `testserver`. Detrás de un
proxy, el proxy debe preservar `Host` y no permitir que el cliente lo falsifique.

La implementación propia en `core/middleware.py` conserva la validación de
Starlette, pero devuelve el sobre común de errores (`bad_request`) con
`request_id`; la respuesta de texto plano de Starlette no cumple el contrato.
Los errores de host conservan las cabeceras CORS porque `CORSMiddleware` queda
por fuera.

### 10.3 Documentación

- `/docs`, `/redoc` y `/openapi.json` solo si `SGA_DOCS_ENABLED=true`.
- En producción, `SGA_DOCS_ENABLED=false`.
- OpenAPI se genera desde los modelos FastAPI/Pydantic.
- Los endpoints nuevos deben declarar `response_model` y respuestas de error
  relevantes.
- No se escribe un `openapi.json` estático a mano.

### 10.4 Cabeceras de seguridad

B3 no implementa una suite completa de cabeceras de seguridad. El proxy de
producción o una fase de endurecimiento debe añadir, como mínimo:

- `Strict-Transport-Security` bajo HTTPS;
- `X-Content-Type-Options: nosniff`;
- `Referrer-Policy`;
- `Content-Security-Policy` para el frontend;
- `X-Frame-Options` o `frame-ancestors` según el despliegue.

No agregar cabeceras que rompan Swagger UI sin probarlas.

---

## 11. Health checks

### 11.1 Separación

- **Liveness** (`/api/v1/health/live`): el proceso responde. No consulta
  PostgreSQL ni Redis.
- **Readiness** (`/api/v1/health/ready`): PostgreSQL y Redis están disponibles.
  Si alguno falla, responde `503`.

Los health checks no requieren autenticación y no revelan DSN, contraseñas,
versiones internas de dependencias ni trazas.

### 11.2 `db/health.py`

Archivo: `backend/src/judicial_archive/db/health.py`

```python
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Literal, Protocol

import structlog
from sqlalchemy import text

from judicial_archive.db.session import Database

HealthState = Literal["ok", "error"]


class RedisPing(Protocol):
    """Contrato minimo de Redis usado por salud; facilita pruebas."""

    def ping(self, **kwargs: Any) -> Any: ...


@dataclass(frozen=True, slots=True)
class DependencyHealth:
    status: HealthState
    latency_ms: float


logger = structlog.get_logger(__name__)


def _elapsed_ms(started: float) -> float:
    return round((perf_counter() - started) * 1000, 2)


async def check_database(
    database: Database | None,
    timeout_seconds: float,
) -> DependencyHealth:
    started = perf_counter()
    if database is None:
        logger.warning("database_health_check_unavailable")
        return DependencyHealth(status="error", latency_ms=0.0)
    try:
        async with asyncio.timeout(timeout_seconds):
            async with database.engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
    except Exception as exc:
        logger.warning(
            "database_health_check_failed",
            error_type=type(exc).__name__,
        )
        return DependencyHealth(status="error", latency_ms=_elapsed_ms(started))
    return DependencyHealth(status="ok", latency_ms=_elapsed_ms(started))


async def check_redis(
    redis: RedisPing | None,
    timeout_seconds: float,
) -> DependencyHealth:
    started = perf_counter()
    if redis is None:
        logger.warning("redis_health_check_unavailable")
        return DependencyHealth(status="error", latency_ms=0.0)
    try:
        async with asyncio.timeout(timeout_seconds):
            await redis.ping()
    except Exception as exc:
        logger.warning(
            "redis_health_check_failed",
            error_type=type(exc).__name__,
        )
        return DependencyHealth(status="error", latency_ms=_elapsed_ms(started))
    return DependencyHealth(status="ok", latency_ms=_elapsed_ms(started))
```

### 11.3 `api/v1/health.py`

Archivo: `backend/src/judicial_archive/api/v1/health.py`

```python
from __future__ import annotations

import asyncio
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request, Response, status
from pydantic import BaseModel, Field
from redis.asyncio import Redis

from judicial_archive import __version__
from judicial_archive.api.deps import get_app_settings
from judicial_archive.core.config import Settings
from judicial_archive.db.health import check_database, check_redis
from judicial_archive.db.session import Database

router = APIRouter()


class LivenessStatus(BaseModel):
    status: Literal["ok"] = "ok"
    service: str
    version: str
    environment: str


class ComponentHealth(BaseModel):
    status: Literal["ok", "error"]
    latency_ms: float = Field(ge=0)


class ReadinessStatus(BaseModel):
    status: Literal["ok", "error"]
    version: str
    components: dict[str, ComponentHealth]


@router.get(
    "/live",
    response_model=LivenessStatus,
    summary="Verificar que el proceso responde",
)
async def liveness(
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> LivenessStatus:
    return LivenessStatus(
        service=settings.app_name,
        version=__version__,
        environment=settings.environment.value,
    )


@router.get(
    "/ready",
    response_model=ReadinessStatus,
    responses={503: {"model": ReadinessStatus}},
    summary="Verificar disponibilidad de dependencias",
)
async def readiness(
    request: Request,
    response: Response,
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> ReadinessStatus:
    database: Database | None = getattr(request.app.state, "database", None)
    redis: Redis | None = getattr(request.app.state, "redis", None)
    db_health, redis_health = await asyncio.gather(
        check_database(database, settings.readiness_timeout_seconds),
        check_redis(redis, settings.readiness_timeout_seconds),
    )
    components = {
        "database": ComponentHealth(
            status=db_health.status,
            latency_ms=db_health.latency_ms,
        ),
        "redis": ComponentHealth(
            status=redis_health.status,
            latency_ms=redis_health.latency_ms,
        ),
    }
    is_ready = all(component.status == "ok" for component in components.values())
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessStatus(
        status="ok" if is_ready else "error",
        version=__version__,
        components=components,
    )
```

### 11.4 Router versionado

Archivo: `backend/src/judicial_archive/api/v1/router.py`

```python
from __future__ import annotations

from fastapi import APIRouter

from judicial_archive.api.v1 import health

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["Salud"])
```

### 11.5 Pruebas asociadas

- liveness `200`, versión y entorno de prueba;
- request-id conservado en liveness;
- request-id generado y seguro;
- readiness sin dependencias `503`;
- readiness con dobles exitosos `200`;
- readiness con una dependencia fallida `503`;
- base de datos disponible y Redis caído `503`;
- errores de dependencia no revelan DSN ni mensajes internos;
- timeout de readiness respetado.

---

## 12. Paginación, ordenamiento y filtros

### 12.1 Contrato de paginación

Parámetros:

- `page`: entero desde 1; defecto 1.
- `page_size`: entero entre 1 y 100; defecto 25.

Respuesta:

```json
{
  "items": [],
  "total": 0,
  "page": 1,
  "page_size": 25,
  "pages": 0,
  "has_next": false,
  "has_previous": false
}
```

Reglas:

- `total` es el total de filas que cumplen los filtros, no el tamaño de la
  página.
- `pages = ceil(total / page_size)`, o 0 si `total = 0`.
- `has_next = page < pages`.
- `has_previous = page > 1 and total > 0`.
- `page_size` nunca supera 100.
- La consulta debe usar `limit` y `offset` calculados en el servidor.
- No se aceptan límites arbitrarios desde el cliente.
- Para listados grandes, el endpoint puede ofrecer cursor en una fase posterior;
  B3 fija el contrato de página.

### 12.2 Ordenamiento

- `sort_by` debe pertenecer a un conjunto explícito de campos permitidos por
  endpoint.
- `order` solo admite `asc` o `desc`.
- Un campo no permitido devuelve `422` con `validation_error`.
- El endpoint debe añadir un desempate estable, por ejemplo `id`, para evitar
  resultados inestables entre páginas.
- No se interpola el nombre del campo directamente en SQL; se mapea a una
  columna segura.

### 12.3 Filtros

B3 no crea un lenguaje genérico de filtros. Reglas:

- Cada endpoint declara filtros explícitos en OpenAPI.
- Los filtros de texto tienen longitud máxima.
- Los filtros de código no aceptan comodines SQL.
- Las fechas se reciben en ISO 8601 y se convierten a `date`/`datetime` con
  validación explícita.
- Un filtro inválido devuelve `422` con `InvalidParameterError`.
- No se aceptan nombres de columna, operadores SQL ni expresiones arbitrarias.
- Los filtros se combinan con AND salvo que el contrato indique lo contrario.
- Los filtros sensibles respetan permisos en B4/B8; B3 no los implementa.
- La paginación debe conservar los mismos filtros y ordenamiento.

### 12.4 Código de paginación

Archivo: `backend/src/judicial_archive/core/pagination.py`

```python
from __future__ import annotations

from collections.abc import Sequence
from enum import StrEnum
from math import ceil
from typing import Annotated, Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel, Field

from judicial_archive.core.errors import InvalidParameterError

T = TypeVar("T")

DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100


class SortOrder(StrEnum):
    ASC = "asc"
    DESC = "desc"


class PageParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


def pagination_params(
    page: Annotated[
        int, Query(ge=1, description="Numero de pagina (empieza en 1).")
    ] = 1,
    page_size: Annotated[
        int,
        Query(ge=1, le=MAX_PAGE_SIZE, description="Elementos por pagina."),
    ] = DEFAULT_PAGE_SIZE,
) -> PageParams:
    return PageParams(page=page, page_size=page_size)


class SortParams(BaseModel):
    sort_by: str | None = None
    order: SortOrder = SortOrder.ASC


def build_sort_params(
    sort_by: str | None,
    order: SortOrder,
    *,
    allowed_fields: frozenset[str],
) -> SortParams:
    if sort_by is not None and sort_by not in allowed_fields:
        raise InvalidParameterError(
            "El campo de ordenamiento no esta permitido.",
            details={"allowed_fields": sorted(allowed_fields)},
        )
    return SortParams(sort_by=sort_by, order=order)


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    pages: int = Field(ge=0)
    has_next: bool
    has_previous: bool

    @classmethod
    def build(cls, items: Sequence[T], *, total: int, params: PageParams) -> Page[T]:
        pages = ceil(total / params.page_size) if total > 0 else 0
        return cls(
            items=list(items),
            total=total,
            page=params.page,
            page_size=params.page_size,
            pages=pages,
            has_next=params.page < pages,
            has_previous=params.page > 1 and total > 0,
        )
```

### 12.5 Ejemplo de uso para fases posteriores

```python
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from judicial_archive.core.pagination import (
    Page,
    PageParams,
    SortOrder,
    build_sort_params,
    pagination_params,
)

router = APIRouter()

_ALLOWED_SORT_FIELDS = frozenset({"number", "created_at"})


@router.get("/boxes", response_model=Page[dict[str, object]])
async def list_boxes(
    params: Annotated[PageParams, Depends(pagination_params)],
    sort_by: Annotated[str | None, Query(max_length=32)] = None,
    order: Annotated[SortOrder, Query()] = SortOrder.ASC,
) -> Page[dict[str, object]]:
    build_sort_params(sort_by, order, allowed_fields=_ALLOWED_SORT_FIELDS)
    return Page[dict[str, object]].build([], total=0, params=params)
```

Este ejemplo es ilustrativo. No crear el endpoint `/boxes` en B3.

### 12.6 Pruebas asociadas

- offset y límite correctos;
- construcción de página con resultados;
- construcción de página vacía;
- campo de ordenamiento no permitido;
- campo permitido y orden descendente;
- `page_size` mayor a 100 rechazado por FastAPI;
- `page=0` rechazado;
- orden inválido rechazado;
- estabilidad de orden documentada y probada en la fase del endpoint.

---

## 13. OpenAPI inicial

### 13.1 Qué debe incluir

- título, versión y descripción de la app;
- etiqueta `Salud`;
- `/api/v1/health/live` con `LivenessStatus`;
- `/api/v1/health/ready` con `ReadinessStatus` y `503`;
- modelos de error comunes cuando se declaren en endpoints;
- esquema de seguridad solo cuando B4 implemente autenticación.

### 13.2 Qué no debe incluir

- endpoints de negocio ficticios;
- tablas o campos internos sin contrato;
- tokens, DSN o ejemplos con secretos;
- esquemas de autenticación no implementados;
- respuestas que el código no produce.

### 13.3 Verificación

```powershell
Set-Location backend
uv run python -c "from tests.helpers import build_test_settings; from judicial_archive.main import create_app; app=create_app(build_test_settings(), configure_logs=False); spec=app.openapi(); print(spec['info']); print(sorted(spec['paths']))"
```

Resultado esperado: solo rutas reales, incluidas las de salud. Si aparece una ruta
que no existe en el router, la documentación no representa el contrato real.

### 13.4 Pruebas asociadas

- `/openapi.json` responde `200` con docs habilitadas;
- el path de liveness existe;
- el path de readiness existe;
- el esquema `ReadinessStatus` incluye `components`;
- `/docs` responde `200` con docs habilitadas;
- `/openapi.json` responde `404` con docs deshabilitadas;
- `/docs` responde `404` con docs deshabilitadas;
- OpenAPI no incluye endpoints de negocio inexistentes.

---

## 14. Límites y protección de endpoints

### 14.1 Controles B3

| Control | Valor / regla | Dónde |
|---|---|---|
| Tamaño de cuerpo | 1 MiB por defecto | `RequestBodyLimitMiddleware` |
| Paginación máxima | 100 elementos | `pagination.py` |
| Timeout de readiness | 3 s por defecto | `config.py` / `db/health.py` |
| Documentación | deshabilitada por defecto | `config.py` / `main.py` |
| Hosts | lista explícita | `TrustedHostMiddleware` |
| CORS | orígenes explícitos, sin `*` | `CORSMiddleware` |
| Errores internos | mensaje genérico | `errors.py` |
| Trazas | solo servidor | `logging.py` / `errors.py` |
| Redacción | claves sensibles | `logging.py` |

### 14.2 Rate limiting

B3 no implementa un limitador de tasa global. Razones:

- requiere identificar actor o IP de forma fiable;
- detrás de proxy, `X-Forwarded-For` no se puede confiar sin configuración;
- límites distintos para login, búsqueda, OCR, descargas y exportaciones;
- un límite global mal ajustado puede bloquear health checks o tráfico legítimo;
- la identidad y las sesiones pertenecen a B4.

Contrato para fases posteriores:

- B4: límite estricto por IP y por usuario en login y recuperación.
- B8: límite para búsquedas costosas y exportaciones.
- B9/B10: límites de tamaño, páginas y tiempo para archivos y OCR.
- B15: límites en el proxy inverso y pruebas de carga.

Mientras no exista, no afirmar que la API tiene rate limiting. Si se implementa
antes, debe usar Redis y una política explícita de fallo, no un diccionario en
memoria por proceso.

### 14.3 Protección de endpoints

B3 no autentica ni autoriza. La protección real de endpoints se implementa en
B4. En B3 solo se garantiza:

- no exponer stack traces;
- no exponer secretos;
- no aceptar cuerpos ilimitados;
- no aceptar hosts no permitidos;
- no aceptar orígenes no configurados;
- no documentar endpoints inexistentes;
- no permitir paginación sin límite.

---

## 15. Pruebas de B3

### 15.1 Matriz

| Área | Archivo | Tipo | Casos mínimos |
|---|---|---|---|
| Configuración | `tests/unit/test_config.py` | unitaria | 12 |
| Paginación | `tests/unit/test_pagination.py` | unitaria | 8 |
| Salud de dependencias | `tests/unit/test_db_health.py` | unitaria | 6 |
| Sesión | `tests/unit/test_session.py` | unitaria | 3 |
| Seguridad | `tests/unit/test_security.py` | unitaria | 5 |
| Logging | `tests/unit/test_logging.py` | unitaria | 6 |
| Errores | `tests/api/test_errors.py` | API | 8 |
| Salud | `tests/api/test_health.py` | API | 8 |
| Middleware | `tests/api/test_middleware.py` | API | 8 |
| CORS y hosts | `tests/api/test_cors_and_hosts.py` | API | 6 |
| OpenAPI | `tests/api/test_openapi.py` | API | 6 |

La cifra exacta puede variar si se agrupan casos, pero ninguna área puede quedar
sin cobertura directa.

### 15.2 `tests/helpers.py`

Archivo: `backend/tests/helpers.py`

```python
from __future__ import annotations

from judicial_archive.core.config import Environment, Settings


def build_test_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "environment": Environment.TEST,
        "debug": False,
        "log_level": "WARNING",
        "log_json": False,
        "database_url": "postgresql+psycopg://sga:sga@localhost:5432/sga_test",
        "redis_url": "redis://localhost:6379/15",
        "secret_key": "test-secret-key-with-at-least-32-characters",
        "trusted_hosts": ["testserver", "localhost"],
        "cors_origins": ["http://localhost:5173"],
        "docs_enabled": True,
        "readiness_timeout_seconds": 0.5,
        "max_request_body_bytes": 1024 * 1024,
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]
```

No usar valores reales de producción. No imprimir `Settings` en fallos.

### 15.3 `tests/conftest.py`

Archivo: `backend/tests/conftest.py`

```python
from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from judicial_archive.core.config import Settings
from judicial_archive.main import create_app
from tests.helpers import build_test_settings


@pytest.fixture
def settings() -> Settings:
    return build_test_settings()


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    app = create_app(settings, configure_logs=False)
    with TestClient(app) as test_client:
        yield test_client
```

`TestClient` ejecuta el lifespan. Para pruebas que necesitan dobles de
PostgreSQL/Redis, se usa `app.state` o `dependency_overrides`, no conexiones
reales.

### 15.4 `tests/api/test_middleware.py`

Archivo: `backend/tests/api/test_middleware.py`

```python
from __future__ import annotations

from fastapi.testclient import TestClient

from judicial_archive.core.config import Settings
from judicial_archive.main import create_app
from tests.helpers import build_test_settings


def _client(**overrides: object) -> TestClient:
    settings: Settings = build_test_settings(**overrides)
    return TestClient(create_app(settings, configure_logs=False))


def test_request_id_is_generated() -> None:
    with _client() as client:
        response = client.get("/api/v1/health/live")
    request_id = response.headers["X-Request-ID"]
    assert len(request_id) == 32
    assert response.json()["status"] == "ok"


def test_valid_request_id_is_preserved() -> None:
    with _client() as client:
        response = client.get(
            "/api/v1/health/live",
            headers={"X-Request-ID": "abc12345"},
        )
    assert response.headers["X-Request-ID"] == "abc12345"


def test_invalid_request_id_is_replaced() -> None:
    with _client() as client:
        response = client.get(
            "/api/v1/health/live",
            headers={"X-Request-ID": "<script>alert(1)</script>"},
        )
    assert response.headers["X-Request-ID"] != "<script>alert(1)</script>"
    assert len(response.headers["X-Request-ID"]) == 32


def test_request_id_on_not_found() -> None:
    with _client() as client:
        response = client.get("/ruta-inexistente")
    assert response.status_code == 404
    assert response.headers["X-Request-ID"]
    assert response.json()["error"]["request_id"] == response.headers["X-Request-ID"]


def test_body_over_limit_returns_413() -> None:
    with _client(max_request_body_bytes=10) as client:
        response = client.post(
            "/api/v1/health/live",
            content=b"x" * 11,
        )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "payload_too_large"


def test_body_within_limit_reaches_app() -> None:
    with _client(max_request_body_bytes=10) as client:
        response = client.get("/api/v1/health/live")
    assert response.status_code == 200


def test_invalid_content_length_returns_400() -> None:
    with _client() as client:
        response = client.post(
            "/api/v1/health/live",
            headers={"Content-Length": "abc"},
        )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "bad_request"


def test_request_id_present_on_validation_error() -> None:
    with _client() as client:
        response = client.get("/api/v1/health/ready?x=1")
    assert response.headers["X-Request-ID"]
```

La prueba de `Content-Length` inválido debe ajustarse si `httpx` normaliza la
cabecera. En ese caso se prueba el middleware directamente con un `scope` ASGI.

### 15.5 `tests/api/test_cors_and_hosts.py`

Archivo: `backend/tests/api/test_cors_and_hosts.py`

```python
from __future__ import annotations

from fastapi.testclient import TestClient

from judicial_archive.main import create_app
from tests.helpers import build_test_settings


def test_cors_preflight_allowed_origin() -> None:
    app = create_app(
        build_test_settings(cors_origins=["http://localhost:5173"]),
        configure_logs=False,
    )
    with TestClient(app) as client:
        response = client.options(
            "/api/v1/health/live",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert response.headers["access-control-allow-credentials"] == "true"


def test_cors_disallowed_origin_has_no_allow_header() -> None:
    app = create_app(
        build_test_settings(cors_origins=["http://localhost:5173"]),
        configure_logs=False,
    )
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/health/live",
            headers={"Origin": "http://evil.example"},
        )
    assert "access-control-allow-origin" not in response.headers


def test_trusted_host_allowed() -> None:
    app = create_app(
        build_test_settings(trusted_hosts=["testserver"]),
        configure_logs=False,
    )
    with TestClient(app) as client:
        response = client.get("/api/v1/health/live")
    assert response.status_code == 200


def test_trusted_host_rejected() -> None:
    app = create_app(
        build_test_settings(trusted_hosts=["example.com"]),
        configure_logs=False,
    )
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/health/live",
            headers={"Host": "evil.example"},
        )
    assert response.status_code == 400


def test_request_id_on_cors_response() -> None:
    app = create_app(
        build_test_settings(cors_origins=["http://localhost:5173"]),
        configure_logs=False,
    )
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/health/live",
            headers={"Origin": "http://localhost:5173"},
        )
    assert response.headers["X-Request-ID"]
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_no_cors_headers_when_no_origins() -> None:
    app = create_app(build_test_settings(cors_origins=[]), configure_logs=False)
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/health/live",
            headers={"Origin": "http://localhost:5173"},
        )
    assert "access-control-allow-origin" not in response.headers
```

### 15.6 `tests/api/test_openapi.py`

Archivo: `backend/tests/api/test_openapi.py`

```python
from __future__ import annotations

from fastapi.testclient import TestClient

from judicial_archive.main import create_app
from tests.helpers import build_test_settings


def test_openapi_contains_only_real_health_paths() -> None:
    app = create_app(build_test_settings(docs_enabled=True), configure_logs=False)
    with TestClient(app) as client:
        response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/health/live" in paths
    assert "/api/v1/health/ready" in paths
    assert not any("boxes" in path for path in paths)


def test_docs_available_when_enabled() -> None:
    app = create_app(build_test_settings(docs_enabled=True), configure_logs=False)
    with TestClient(app) as client:
        response = client.get("/docs")
    assert response.status_code == 200


def test_openapi_disabled() -> None:
    app = create_app(build_test_settings(docs_enabled=False), configure_logs=False)
    with TestClient(app) as client:
        response = client.get("/openapi.json")
    assert response.status_code == 404


def test_docs_disabled() -> None:
    app = create_app(build_test_settings(docs_enabled=False), configure_logs=False)
    with TestClient(app) as client:
        response = client.get("/docs")
    assert response.status_code == 404


def test_readiness_schema_is_documented() -> None:
    app = create_app(build_test_settings(docs_enabled=True), configure_logs=False)
    with TestClient(app) as client:
        response = client.get("/openapi.json")
    schemas = response.json()["components"]["schemas"]
    assert "ReadinessStatus" in schemas
    assert "components" in schemas["ReadinessStatus"]["properties"]


def test_health_tag_is_documented() -> None:
    app = create_app(build_test_settings(docs_enabled=True), configure_logs=False)
    with TestClient(app) as client:
        response = client.get("/openapi.json")
    tags = response.json()["tags"]
    assert any(tag["name"] == "Salud" for tag in tags)
```

### 15.7 Pruebas de logging

Archivo: `backend/tests/unit/test_logging.py`

```python
from __future__ import annotations

from judicial_archive.core.logging import _redact_sensitive_values


def test_redacts_top_level_secret() -> None:
    event = {"password": "secret", "user": "admin"}
    result = _redact_sensitive_values(None, "info", dict(event))
    assert result["password"] == "***"
    assert result["user"] == "admin"


def test_redacts_nested_dict() -> None:
    event = {"payload": {"token": "abc", "name": "x"}}
    result = _redact_sensitive_values(None, "info", dict(event))
    nested = result["payload"]
    assert isinstance(nested, dict)
    assert nested["token"] == "***"
    assert nested["name"] == "x"


def test_redacts_list_and_tuple() -> None:
    event = {"items": [{"secret": "a"}, {"ok": "b"}]}
    result = _redact_sensitive_values(None, "info", dict(event))
    items = result["items"]
    assert isinstance(items, list)
    assert items[0]["secret"] == "***"
    assert items[1]["ok"] == "b"
    tuple_result = _redact_sensitive_values(
        None,
        "info",
        {"value": ({"password": "a"},)},
    )
    assert tuple_result["value"][0]["password"] == "***"


def test_redacts_database_url() -> None:
    result = _redact_sensitive_values(
        None,
        "info",
        {"database_url": "postgresql+psycopg://u:secret@host/db"},
    )
    assert result["database_url"] == "***"


def test_redacts_redis_url_and_dsn() -> None:
    result = _redact_sensitive_values(
        None,
        "info",
        {"redis_url": "redis://:secret@host/0", "dsn": "postgresql://u:secret@host/db"},
    )
    assert result["redis_url"] == "***"
    assert result["dsn"] == "***"


def test_does_not_mutate_unrelated_keys() -> None:
    event = {"request_id": "abc", "count": 3, "ok": True}
    result = _redact_sensitive_values(None, "info", dict(event))
    assert result == event
```

### 15.8 Pruebas de readiness con dobles

Archivo: `backend/tests/api/test_health.py`

```python
from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from judicial_archive.main import create_app
from tests.helpers import build_test_settings


class _HealthyDatabase:
    class _Engine:
        class _Connection:
            async def __aenter__(self) -> _HealthyDatabase._Engine._Connection:
                return self

            async def __aexit__(self, *args: object) -> None:
                return None

            async def execute(self, *args: object, **kwargs: object) -> None:
                return None

        def connect(self) -> _HealthyDatabase._Engine._Connection:
            return self._Connection()

    engine = _Engine()


class _BrokenDatabase:
    class _Engine:
        def connect(self) -> Any:
            raise RuntimeError("no disponible")

    engine = _Engine()


class _HealthyRedis:
    async def ping(self, **kwargs: object) -> bool:
        return True


class _BrokenRedis:
    async def ping(self, **kwargs: object) -> bool:
        raise RuntimeError("no disponible")


def _client_with_state(database: object, redis: object) -> TestClient:
    app = create_app(build_test_settings(), configure_logs=False)
    client = TestClient(app)
    client.__enter__()
    app.state.database = database
    app.state.redis = redis
    return client


def test_ready_when_dependencies_are_healthy() -> None:
    client = _client_with_state(_HealthyDatabase(), _HealthyRedis())
    try:
        response = client.get("/api/v1/health/ready")
    finally:
        client.__exit__(None, None, None)
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_not_ready_when_database_fails() -> None:
    client = _client_with_state(_BrokenDatabase(), _HealthyRedis())
    try:
        response = client.get("/api/v1/health/ready")
    finally:
        client.__exit__(None, None, None)
    assert response.status_code == 503
    assert response.json()["components"]["database"]["status"] == "error"


def test_not_ready_when_redis_fails() -> None:
    client = _client_with_state(_HealthyDatabase(), _BrokenRedis())
    try:
        response = client.get("/api/v1/health/ready")
    finally:
        client.__exit__(None, None, None)
    assert response.status_code == 503
    assert response.json()["components"]["redis"]["status"] == "error"
```

Los dobles deben respetar el contrato mínimo; no se simula una conexión real de
SQLAlchemy más allá de `connect()` y `execute()`.

### 15.9 Criterios de cobertura

- Las ramas nuevas de configuración, middleware, errores y logging deben estar
  cubiertas.
- No se acepta subir el umbral global para ocultar módulos sin probar; el umbral
  se mantiene en 75 y la cobertura real no debe bajar de 90 % en `core`.
- Las pruebas API no dependen de PostgreSQL ni Redis reales.
- Las pruebas de integración se mantienen y se ejecutan por separado.

---

## 16. Comandos de implementación y verificación

### 16.1 Preparación

```powershell
Set-Location backend
uv sync --all-groups
```

No ejecutar `pip install` global ni crear un entorno virtual fuera de `uv`.

### 16.2 Calidad estática

```powershell
Set-Location backend
uv run ruff check .
uv run ruff format --check .
uv run mypy src
```

Corrección automática permitida solo para formato e imports seguros:

```powershell
uv run ruff check . --fix
uv run ruff format .
```

Revisar el diff después de `--fix`; no aceptar cambios no relacionados.

### 16.3 Pruebas rápidas

```powershell
Set-Location backend
uv run pytest tests/unit -q --no-cov
uv run pytest tests/api -q --no-cov
```

### 16.4 Suite completa

```powershell
Set-Location backend
uv run pytest tests -q
```

La suite completa incluye integración. Si no hay PostgreSQL/Redis de prueba,
saltar integración de forma explícita y registrarlo:

```powershell
uv run pytest tests -q -m "not integration"
```

No presentar ese resultado como suite completa.

### 16.5 Integración

```powershell
Set-Location backend
$env:RUN_INTEGRATION = "1"
$env:TEST_DATABASE_URL = "postgresql+psycopg://sga:CLAVE@localhost:5432/sga_test"
$env:TEST_REDIS_URL = "redis://localhost:6379/15"
uv run pytest tests/integration -q -n 0
```

Reglas:

- La base debe ser `sga_test`, nunca `sga_dev` ni producción.
- No imprimir la contraseña.
- No ejecutar integración en paralelo contra la misma base.
- No revertir migraciones de desarrollo.
- Limpiar datos de prueba solo con fixtures controlados.

### 16.6 Migraciones

```powershell
Set-Location backend
uv run alembic check
```

B3 no agrega migraciones. Si `alembic check` detecta cambios, no son de B3 salvo
que el equipo confirme lo contrario.

### 16.7 Servidor local

```powershell
Set-Location backend
uv run uvicorn judicial_archive.asgi:app --reload --host 127.0.0.1 --port 8000 --loop judicial_archive.core.runtime:selector_loop_factory
```

Comprobaciones:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health/live | ConvertTo-Json -Depth 5
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health/ready | ConvertTo-Json -Depth 5
```

Si readiness falla, revisar PostgreSQL y Redis; no desactivar el check para
“hacer pasar” la prueba.

### 16.8 Revisión de diff

```powershell
Set-Location ..
git status --short
git diff --check
git diff --stat
```

No hacer commit ni push en B3 sin autorización explícita.

---

## 17. Checklist de aceptación B3

### 17.1 Configuración

- [x] `max_request_body_bytes` existe con defecto 1 MiB y rango válido.
- [x] Producción exige `debug=false`.
- [x] Producción exige `docs_enabled=false`.
- [x] Producción exige `log_json=true`.
- [x] Producción exige `session_cookie_secure=true`.
- [x] Producción rechaza `*` y `testserver` en hosts.
- [x] Orígenes CORS se validan.
- [x] Las listas se parsean sin espacios vacíos.
- [x] Los errores de validación no imprimen secretos.

### 17.2 Aplicación

- [x] `create_app` acepta `Settings` y `configure_logs`.
- [x] Lifespan crea y cierra PostgreSQL/Redis.
- [x] `RequestContextMiddleware` es el más externo.
- [x] CORS está dentro del request-id.
- [x] `TrustedHostMiddleware` está configurado.
- [x] `RequestBodyLimitMiddleware` está activo.
- [x] `asgi.py` exporta `app`.
- [x] Las dependencias no hacen commit automático.

### 17.3 Logging y errores

- [x] Logging JSON en producción.
- [x] Logging legible en desarrollo.
- [x] `request_id` se propaga.
- [x] Redacción recursiva de secretos.
- [x] No se duplican handlers de uvicorn.
- [x] Todos los errores usan el sobre común.
- [x] `413` está en el catálogo y mapeado.
- [x] Los `500` no exponen detalles internos.
- [x] Los errores de validación no reenvían valores.

### 17.4 API

- [x] Liveness no consulta dependencias.
- [x] Readiness consulta PostgreSQL y Redis.
- [x] Readiness devuelve `503` si falla una dependencia.
- [x] Los health checks no revelan secretos.
- [x] Paginación limitada a 100.
- [x] Ordenamiento validado contra campos permitidos.
- [x] No existe un DSL genérico de filtros.
- [x] OpenAPI solo documenta rutas reales.
- [x] Docs se deshabilitan con la configuración.
- [x] No se implementa rate limiting en B3.

### 17.5 Pruebas y calidad

- [x] `ruff check` pasa.
- [x] `ruff format --check` pasa.
- [x] `mypy src tests` pasa.
- [x] `pytest tests/unit` pasa.
- [x] `pytest tests/api` pasa.
- [x] `pytest tests` pasa con integración habilitada.
- [x] Cobertura global ≥ 75 %.
- [x] Cobertura de `core` ≥ 90 %.
- [x] `alembic check` sin cambios inesperados.
- [x] `git diff --check` sin errores.

---

## 18. Riesgos y decisiones pendientes

| Riesgo | Impacto | Mitigación |
|---|---|---|
| `Content-Length` ausente o chunked | Límite de cuerpo evadible | Proxy con límite duro; resolver en B9 |
| Confianza en `X-Forwarded-For` | Rate limiting incorrecto | No implementarlo en B3; configurar proxy en B15 |
| Redacción solo por clave | Secretos en texto libre | Prohibir secretos en mensajes; revisar logs |
| CORS mal configurado | Exposición o bloqueo del frontend | Orígenes explícitos y pruebas |
| Docs en producción | Exposición de superficie | `docs_enabled=false` obligatorio |
| Health readiness costoso | Sobrecarga por sondas | Timeout corto y frecuencia controlada |
| Orden de middleware incorrecto | Sin request-id en errores CORS/host | Probar orden y cabeceras |
| Rate limiting en memoria | Límites inconsistentes | Usar Redis en B4/B8 |
| Filtros genéricos | Inyección o consultas costosas | Filtros explícitos y campos permitidos |
| Cobertura alta artificial | Deuda oculta | Revisar ramas, no solo porcentaje |
| Dependencia de `TestClient` | Diferencias con producción | Pruebas ASGI directas para middleware |
| Auditoría incompleta | Falta de trazabilidad | Completar en B4/B8 |

Decisiones pendientes que no bloquean B3:

- si el límite de cuerpo se configura por entorno o por ruta;
- si readiness incluye versión de base de datos;
- si se añaden cabeceras de seguridad en la app o solo en el proxy;
- política de retención de logs;
- límites de tasa por endpoint.

Ninguna de estas decisiones autoriza a implementar autenticación, rate limiting
o endpoints de negocio en B3.

---

## 19. Handoff a fases posteriores

### B4 — Autenticación y sesiones

- Implementar login, logout, sesiones y CSRF.
- Añadir esquema de seguridad a OpenAPI.
- Aplicar límites de tasa en login.
- Proteger endpoints con dependencias de autorización.
- Auditar accesos y cambios.
- No reutilizar el request-id como identificador de usuario.

### B5/B6 — Expedientes y documentos

- Reutilizar paginación y errores.
- Definir filtros explícitos por endpoint.
- Añadir códigos de negocio al catálogo.
- No devolver entidades ORM directamente.

### B8 — Búsqueda

- Aplicar límites de tasa y tiempo.
- Limitar tamaño de consultas y resultados.
- Documentar coste y paginación.
- Evitar filtros SQL arbitrarios.

### B9/B10 — Archivos y OCR

- Sustituir el límite simple por límites por tipo y tamaño.
- Validar MIME real, no solo extensión.
- Analizar archivos en cuarentena.
- Añadir timeouts y límites de páginas.
- Resolver cuerpos `chunked` con límite de streaming.

### B15 — Producción

- Configurar proxy, TLS, HSTS y cabeceras.
- Limitar tasa en el borde.
- Restringir hosts y orígenes reales.
- Deshabilitar docs.
- Verificar logs sin secretos.
- Ejecutar pruebas de carga y caos.

---

## 20. Registro de validación

Completar después de implementar y ejecutar. No marcar como aprobado sin
evidencia.

| Comprobación | Comando | Resultado | Fecha |
|---|---|---|---|
| Ruff lint | `uv run ruff check src tests` | Pasa | 2026-10-26 |
| Ruff format | `uv run ruff format --check src tests` | 85 archivos ya formateados | 2026-10-26 |
| Mypy | `uv run mypy src tests` | Sin errores en 85 archivos | 2026-10-26 |
| Unitarias | `uv run pytest tests/unit -q --no-cov -n 0` | 52 passed | 2026-10-26 |
| API | `uv run pytest tests/api -q --no-cov -n 0` | 32 passed | 2026-10-26 |
| Integración | `uv run pytest tests/integration -q --no-cov -n 0` con entorno de prueba | 46 passed | 2026-10-26 |
| Suite completa | `uv run pytest tests -q -n 0` con integración | 130 passed | 2026-10-26 |
| Cobertura | misma suite completa | 95,03 % global; 95 % en `core` | 2026-10-26 |
| Alembic | `uv run alembic check` | Sin operaciones nuevas | 2026-10-26 |
| Pre-commit | `uv run pre-commit run --all-files` | Todos los hooks pasan | 2026-10-26 |
| Diff | `git diff --check` | Sin errores | 2026-10-26 |
| Smoke local | Uvicorn con PostgreSQL/Redis y `--loop ...` | `live=ok`, `ready=200`, `db=ok`, `redis=ok`; host no permitido `400 bad_request` | 2026-10-26 |

### 20.1 Evidencia

- Ruff lint y formato sin hallazgos; mypy sin errores en `src` y `tests`.
- 52 pruebas unitarias, 32 de API y 46 de integración: 130 aprobadas.
- Cobertura global 95,03 %; cobertura de `core` 95 %.
- `alembic check`: “No new upgrade operations detected.”
- Smoke local: `live=ok`, `ready_status=200`, `db=ok`, `redis=ok` y host no
  permitido con `400 bad_request`, usando
  `--loop judicial_archive.core.runtime:selector_loop_factory`.
- Pre-commit: todos los hooks pasan, incluidos Ruff, mypy y detección de
  secretos.
- `git diff --check` sin espacios finales ni conflictos.
- No se añadieron secretos ni datos reales; `.env` sigue ignorado.

### 20.2 Desviaciones aceptadas

- `httpx2>=2.16,<3` se añadió solo a dependencias de desarrollo porque el
  `TestClient` de Starlette 1.9 lo requiere; con `httpx` emite una advertencia
  que pytest convierte en error. Es BSD-3-Clause, mantenido por Pydantic,
  requiere Python ≥ 3.11 y no se usa en producción. `httpx` se conserva para
  pruebas asíncronas.
- En Windows se añadió `selector_loop_factory()` y los comandos usan
  `--loop judicial_archive.core.runtime:selector_loop_factory`. Uvicorn 0.54
  crea el loop antes de importar la app; cambiar la política en `main.py` no
  evita el `InterfaceError` de psycopg con el loop Proactor.
- `TrustedHostMiddleware` se implementó en `core/middleware.py` para devolver
  el sobre común con `request_id`; la respuesta de texto plano de Starlette no
  cumple el contrato. Mantiene la misma validación de `Host`.
- Para integración se usa la base `sga_test` con un usuario con permisos sobre
  su esquema `public`. Al derivar `TEST_DATABASE_URL` desde `SGA_DATABASE_URL`,
  sustituir solo el nombre final de la base, no el usuario. El fixture de tests
  oculta la URL en repr para no filtrar credenciales en fallos.

### 20.3 Estado de la guía

B3 está cerrada con la evidencia anterior. Esta guía sigue siendo la referencia
de implementación y debe actualizarse si cambia el contrato de la capa común.
