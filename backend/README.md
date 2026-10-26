# SGA Backend

Backend del Sistema de Gestión Documental Judicial.

La documentación principal está en el README raíz y en `../docs/`.

## Requisitos

- Python 3.12 gestionado por `uv`.
- PostgreSQL 18 con las bases `sga_dev` y `sga_test`.
- Redis 7.4 o superior.

## Configuración

```powershell
uv sync
Copy-Item .env.example .env
# Editar .env con las credenciales locales.
```

## Comandos

```powershell
uv run uvicorn judicial_archive.asgi:app --reload --loop judicial_archive.core.runtime:selector_loop_factory
uv run arq judicial_archive.tasks.worker.WorkerSettings
uv run alembic current
uv run alembic upgrade head
uv run ruff format .
uv run ruff check .
uv run mypy src tests
uv run pytest
.\scripts\check.ps1
```

## Pruebas de integración

Con PostgreSQL y Redis disponibles:

```powershell
$env:RUN_INTEGRATION = "1"
$env:TEST_DATABASE_URL = "postgresql+psycopg://usuario:clave@localhost:5432/sga_test"
$env:TEST_REDIS_URL = "redis://localhost:6379/15"
uv run pytest tests/integration -q --no-cov -n 0
```

Usar un usuario con permisos sobre `public` en `sga_test`. No ejecutar en
paralelo contra la misma base ni imprimir credenciales.

## Documentación

- `../docs/arquitectura.md`
- `../docs/api.md`
- `../docs/instalacion-desarrollo.md`
- `../docs/pruebas.md`
- `../docs/seguridad.md`
- `../docs/pendientes-de-validacion.md`
- `../docs/decisiones/ADR-*.md`
- `../docs/AGENTS.md`

## Estado

B3 completada: configuración, errores uniformes, logging, middleware,
salud, paginación y OpenAPI común. Incluye el esquema persistente de B2 y
sus migraciones; todavía no hay endpoints de negocio ni autenticación.
Validación: 130 pruebas, cobertura global 95,03 %, `core` 95 %.
