$ErrorActionPreference = "Stop"
$backendRoot = Split-Path -Parent $PSScriptRoot
Push-Location $backendRoot
try {
    uv run arq judicial_archive.tasks.worker.WorkerSettings
}
finally {
    Pop-Location
}
