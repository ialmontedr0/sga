# Instalación y desarrollo

## 1. Requisitos
- Windows 10/11 con PowerShell 5.1 o superior.
- Git 2.40+.
- PostgreSQL 18 con `psql` en PATH.
- Redis 7.4+ (servicio o contenedor local).
- uv 0.8+.

## 2. Clonar

```powershell
git clone https://github.com/ialmontedr0/sga.git sga
Set-Location sga
```

## 3. Python y dependencias

```powershell
uv python install 3.12
Set-Location backend
uv python pin 3.12
uv sync
```

## 4. Bases de datos

Abrir `psql` como administrador:

```powershell
psql -U postgres
```

```sql
CREATE ROLE sga_dev LOGIN PASSWORD 'CAMBIAR_CONTRASENA_DEV';
CREATE DATABASE sga_dev OWNER sga_dev ENCODING 'UTF8';
CREATE ROLE sga_test LOGIN PASSWORD 'CAMBIAR_CONTRASENA_TEST';
CREATE DATABASE sga_test OWNER sga_test ENCODING 'UTF8';
```

Verificar:

```powershell
psql -U sga_dev -d sga_dev -c "SELECT current_database(), current_user;"
psql -U sga_test -d sga_test -c "SELECT current_database(), current_user;"
```

## 5. Redis

```powershell
redis-cli ping
# Esperado: PONG
```

En Windows, si Redis corre como servicio:

```powershell
Get-Service *redis*
```

## 6. Configuración

```powershell
Copy-Item .env.example .env
```

Editar `.env` y generar un secreto:

```powershell
uv run python -c "import secrets; print(secrets.token_urlsafe(48))"
```

No versionar `.env`.

## 7. Migraciones

```powershell
uv run alembic upgrade head
uv run alembic current
```

## 8. Ejecutar

```powershell
uv run uvicorn judicial_archive.asgi:app --reload --loop judicial_archive.core.runtime:selector_loop_factory
```

En Windows debe usarse el loop Selector para psycopg async. El script
`.\scripts\dev.ps1` ya aplica esa configuración.

- `http://127.0.0.1:8000/api/v1/health/live`
- `http://127.0.0.1:8000/api/v1/health/ready`
- `http://127.0.0.1:8000/docs`

## 9. Worker

```powershell
uv run arq judicial_archive.tasks.worker.WorkerSettings
```

## 10. Calidad

```powershell
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
uv run pytest
.\scripts\check.ps1
```

## 11. Problemas frecuentes
- `password authentication failed`: revisar usuario, base y `pg_hba.conf`.
- `database does not exist`: crear la base y ejecutar migraciones.
- `Connection refused` en Redis: iniciar el servicio y verificar el puerto.
- `port already in use`: detener el proceso anterior o cambiar el puerto.
- `UnicodeDecodeError`: guardar archivos en UTF-8 sin BOM.
- `ruff` no encontrado: ejecutar con `uv run` desde `backend/`.
- mypy no encuentra el paquete: `uv sync` y ejecutar dentro de `backend/`.
- Pylance marca `is unknown import symbol`: eliminar stubs viejos en `typings/` (Pylance los usa antes que el paquete real) y seleccionar `backend/.venv`.
- Pylance marca `Expected no type arguments for class "Redis"`: redis-py 5.x no es genérico; usar `Redis`, no `Redis[str]`.
- Pylance marca `ORJSONResponse is deprecated`: usar `JSONResponse`; FastAPI 0.161 serializa con Pydantic.
- Pylance marca `Settings()` con argumentos faltantes: usar `# pyright: ignore[reportCallIssue]`, no `# type: ignore`.
- `InterfaceError` en readiness con PostgreSQL en Windows: iniciar
  Uvicorn con `--loop judicial_archive.core.runtime:selector_loop_factory`
  o usar `.\scripts\dev.ps1`; el loop Proactor no es compatible con
  psycopg async.
- Alembic falla con `ProactorEventLoop`: usar el engine síncrono de `env.py` o `configure_event_loop_policy()` en Windows.
- ARQ falla con `at least one function or cron_job must be registered`: registrar al menos `healthcheck`.
- PowerShell bloquea scripts: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

## 12. Flujo diario

1. `git switch -c feat/<tema>`
2. Implementar con pruebas.
3. Ejecutar `.\scripts\check.ps1`.
4. Revisar `git diff`.
5. Commit convencional.
6. Push y PR.
