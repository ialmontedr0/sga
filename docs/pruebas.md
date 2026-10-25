# Pruebas

## Pirámide
- Unitarias: reglas, configuración, seguridad, paginación.
- API: contratos, errores, cabeceras, autenticación.
- Integración: PostgreSQL y Redis reales.
- Seguridad: permisos, CSRF, fuerza bruta, archivos (fases posteriores).
- E2E: frontend y flujos completos (fases F).

## Comandos
cd backend
uv run pytest
uv run pytest tests/unit
uv run pytest tests/api
uv run pytest -m integration
uv run pytest --cov=judicial_archive --cov-report=html

## Integración
$env:RUN_INTEGRATION = "1"
uv run pytest -m integration
Remove-Item Env:RUN_INTEGRATION

Requiere PostgreSQL y Redis. Usa `sga_test` y la base Redis 15.

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
- Cobertura objetivo: 60 % en B0, 75 % al cierre de B2 y 85 % al cierre de B16.

## Criterio de aceptación
Todas las pruebas pasan en local y CI; las de integración se ejecutan en
CI con servicios reales.
