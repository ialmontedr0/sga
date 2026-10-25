$ErrorActionPreference = "Stop"
$backendRoot = Split-Path -Parent $PSScriptRoot
Push-Location $backendRoot
try {
    uv run uvicorn judicial_archive.asgi:app --reload --host 127.0.0.1 --port 8000
}
finally {
    Pop-Location
}
