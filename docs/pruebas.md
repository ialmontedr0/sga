# Pruebas

## Pirámide
- Unitarias: reglas, configuración, seguridad, paginación.
- API: contratos, errores, cabeceras, autenticación.
- Integración: PostgreSQL y Redis reales.
- Seguridad: permisos, CSRF, fuerza bruta, archivos (fases posteriores).
- E2E: frontend y flujos completos (fases F).

## Comandos
```powershell
Set-Location backend
uv run pytest -n 0
uv run pytest tests/unit -q --no-cov -n 0
uv run pytest tests/api -q --no-cov -n 0
uv run pytest tests/integration -q --no-cov -n 0
uv run pytest --cov=judicial_archive --cov-report=html -n 0
```

Las pruebas de API usan `fastapi.testclient.TestClient`. Starlette 1.9
requiere `httpx2` para evitar la deprecación de `httpx`; se mantiene como
dependencia de desarrollo.

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
Todas las pruebas pasan en local y CI; las de integración se ejecutan en
CI con servicios reales.
