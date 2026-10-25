# SGA Backend

Backend del Sistema de Gestión Documental Judicial.

La documentación principal está en el README raíz y en `../docs/`.
Comandos básicos:

```powershell
uv sync
uv run uvicorn judicial_archive.asgi:app --reload
uv run pytest

- **Redis se fija en `<6`** porque ARQ 0.28 declara `redis>=4.2,<6`. Instalar redis-py 8 provocaría un conflicto de resolución. redis-py 5.3 funciona correctamente con servidores Redis 7 y 8.
- **Python 3.12** se elige por compatibilidad con el ecosistema de OCR, visión y procesamiento documental que se evaluará en B11. No se usa 3.13/3.14 en B0.
- **`arq` se fija `<0.29`** porque es una versión 0.x; una actualización menor puede introducir cambios incompatibles. Se revisará en B10/B11.
- **No se incluyen dependencias de OCR, imágenes, PDF ni frontend** en B0. Se agregarán cuando la fase correspondiente las requiera.
- `uv.lock` es la fuente de reproducibilidad. Se versiona y no se edita a mano.
