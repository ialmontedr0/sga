# ADR-0008 --- Ruff, mypy, pytest y CI obligatorio

- Estado: aceptada
- Fecha: 2026-10-23

## Contexto
El proyecto tendrá un solo equipo pequeño y debe mantener calidad sin
revisiones manuales repetitivas.

## Decisión
Ruff para formato y lint, mypy estricto, pytest con cobertura, pre-commit
con gitleaks y CI en GitHub Actions con PostgreSQL y Redis reales.
`uv sync --frozen` garantiza el lock.

## Alternativas
- Black + isort + flake8: más herramientas y más lento.
- Solo revisión manual: no escala ni es reproducible.

## Consecuencias
- Comprobaciones automáticas y consistentes.
- El CI requiere servicios y lock actualizado.
- Los hooks locales pueden ralentizar commits grandes.

## Referencias
`.pre-commit-config.yaml`, `.github/workflows/ci.yml`.
