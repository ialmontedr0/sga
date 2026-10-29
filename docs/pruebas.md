# Pruebas

## Pirámide

- Unitarias: reglas, configuración, seguridad, paginación.
- API: contratos, errores, cabeceras, autenticación.
- Integración: PostgreSQL y Redis reales.
- Seguridad: permisos, CSRF, fuerza bruta, archivos (fases posteriores).
- E2E: frontend y flujos completos (fases F).

## Comandos generales

```powershell
Set-Location backend
uv run pytest -n 0
uv run pytest tests/unit -q --no-cov -n 0
uv run pytest tests/api -q --no-cov -n 0
uv run pytest tests/integration -q --no-cov -n 0
uv run pytest --cov=judicial_archive --cov-report=html -n 0
```

Las pruebas de API usan `fastapi.testclient.TestClient`. Starlette 1.9
requiere `httpx2` para evitar la deprecación de `httpx`; se mantiene como dependencia de desarrollo.

## Integración

```powershell
$env:RUN_INTEGRATION = "1"
$env:TEST_DATABASE_URL = "postgresql+psycopg://usuario:clave@localhost:5432/sga_test"
$env:TEST_REDIS_URL = "redis://localhost:6379/15"
uv run pytest tests/integration -q --no-cov -n 0
Remove-Item Env:RUN_INTEGRATION, Env:TEST_DATABASE_URL, Env:TEST_REDIS_URL
```

Requiere PostgreSQL y Redis. Usa `sga_test` y la base Redis 15 con un
usuario que tenga permisos sobre `public`. Si se deriva desde
`SGA_DATABASE_URL`, sustituir solo el nombre final de la base, no el
usuario. No imprimir credenciales ni ejecutar la integración en paralelo
contra la misma base.

## Datos

- Sintéticos.
- NUC `00001` y `2022-102-00001`.
- Códigos 589 y 107 repetidos.
- Fechas parciales y desconocidas.
- Documentos sin ubicación.
- Archivos pequeños de prueba.

## Reglas

- Toda corrección incluye prueba de regresión.
- Sin dependencia del orden.
- Sin fechas reales no controladas.
- Sin secretos ni datos personales.
- Sin mocks de PostgreSQL para reglas de persistencia.
- Cobertura global mínima: 75 %; cobertura de `core` mínima: 90 % en B3.
- Cobertura objetivo: 60 % en B0, 75 % al cierre de B2 y 85 % al cierre de B16.

## Estado B3 (2026-10-26)

- 52 unitarias, 32 de API y 46 de integración: 130 aprobadas.
- Cobertura global 95,03 %; `core` 95 %.
- Ruff, formato, mypy y `alembic check` sin errores.

## Criterio de aceptación

Todas las pruebas pasan en local y CI; las de integración se ejecutan en CI con servicios reales.

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
