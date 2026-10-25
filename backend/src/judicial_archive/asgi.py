from __future__ import annotations

from judicial_archive.main import create_app

app = create_app()

# Uso:
# uv run uvicorn judicial_archive.asgi:app --reload --host 127.0.0.1 --port 8000
