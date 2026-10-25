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
uv run uvicorn judicial_archive.asgi:app --reload
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
uv run pytest tests/integration
```

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

B0 implementada como base técnica. No contiene todavía modelos de negocio,
migraciones de dominio ni endpoints funcionales.
