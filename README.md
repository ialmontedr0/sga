# SGA --- Sistema de Gestión Documental Judicial

Sistema web para administrar el archivo central judicial: cajas,
expedientes, documentos administrativos, ubicaciones físicas,
digitalización, movimientos, préstamos, auditoría e inventario.

El backend se construye primero. El frontend se incorpora cuando existan
contratos de API probados.

## Estado

Fase actual: **B3 completada**; siguiente fase: **B4 --- Autenticación,
autorización y administración de usuarios**.

El repositorio contiene la base técnica y persistente del backend:
configuración, esquema SQLAlchemy con migraciones, errores uniformes,
logging, middleware, pruebas y salud. No contiene aún endpoints de
negocio ni autenticación.

## Stack

- Python 3.12, uv.
- FastAPI, Uvicorn, Pydantic v2.
- PostgreSQL 18, SQLAlchemy 2.1 async, psycopg 3, Alembic.
- Redis 7.4+, ARQ.
- Ruff, mypy, pytest, pre-commit, GitHub Actions.
- Frontend previsto: React, TypeScript, Vite, Tailwind CSS.

## Requisitos

- Windows 10/11, Linux o macOS.
- Python 3.12 gestionado por uv.
- PostgreSQL 18 con las bases `sga_dev` y `sga_test`.
- Redis 7.4 o superior.
- Git.

Ver `docs/instalacion-desarrollo.md` para el procedimiento detallado.

## Inicio rápido

```powershell
git clone https://github.com/ialmontedr0/sga.git sga
Set-Location sga
uv python install 3.12
Set-Location backend
uv sync
Copy-Item .env.example .env
# Editar .env con credenciales locales reales.
uv run alembic upgrade head
uv run uvicorn judicial_archive.asgi:app --reload --loop judicial_archive.core.runtime:selector_loop_factory
```

Abrir `http://127.0.0.1:8000/docs`. En Windows, el loop Selector es
obligatorio para que psycopg async funcione; `.\scripts\dev.ps1` ya lo
configura.

## Comandos

```powershell
cd backend
uv sync
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

## Estructura

```text
backend/
├── src/judicial_archive/   Código del backend
│   ├── core/               Configuración, errores, logging, seguridad
│   ├── db/                 Motor, sesiones y salud
│   ├── api/                Dependencias y rutas versionadas
│   ├── modules/            Dominio (se crea por fase)
│   └── tasks/              Worker ARQ
├── tests/                  Unitarias, API e integración
├── alembic/                Migraciones
└── scripts/                Utilidades de desarrollo
docs/                       Documentación y ADR
```

## Documentación

- `docs/arquitectura.md`
- `docs/api.md`
- `docs/instalacion-desarrollo.md`
- `docs/pruebas.md`
- `docs/seguridad.md`
- `docs/pendientes-de-validacion.md`
- `docs/decisiones/ADR-*.md`
- `docs/AGENTS.md` (reglas maestras)
- `docs/phases/GUIA_DESARROLLO_FASES_SGA.md`

## Seguridad

No se aceptan secretos, documentos judiciales reales, volcados de base de
datos ni datos personales en el repositorio. Los documentos se almacenan
en un volumen privado y se sirven mediante endpoints autorizados.

## Licencia

Uso institucional. Pendiente de definición formal.
