# ADR-0001 --- Python 3.12, uv y layout src

- Estado: aceptada
- Fecha: 2026-10-23

## Contexto
El backend requiere tipado estricto, dependencias reproducibles y
compatibilidad con Windows y Linux. El entorno tiene Python 3.10.8, pero
FastAPI, SQLAlchemy y las herramientas modernas se benefician de 3.12.

## Decisión
Usar Python 3.12 gestionado por uv, layout `src/`, paquete
`judicial_archive` y distribución `sga-backend`. Versionar `uv.lock`.

## Alternativas
- Python 3.10 del sistema: menor vida útil y sin ventajas.
- Poetry: válido, pero uv es más rápido y ya está instalado.
- Layout plano: expone el directorio de trabajo en importaciones.

## Consecuencias
- Reproducibilidad y velocidad.
- Requiere instalar 3.12 con uv en cada entorno.
- El paquete debe instalarse con `uv sync`.

## Referencias
`pyproject.toml`, `docs/instalacion-desarrollo.md`.
