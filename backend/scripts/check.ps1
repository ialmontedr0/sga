$ErrorActionPreference = "Stop"

function Invoke-Step {
    param(
        [Parameter(Mandatory = $true)][string] $Name,
        [Parameter(Mandatory = $true)][scriptblock] $Command
    )

    Write-Host "==> $Name" -ForegroundColor Cyan
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "Fallo en '$Name' con codigo $LASTEXITCODE."
    }
}

$backendRoot = Split-Path -Parent $PSScriptRoot
Push-Location $backendRoot
try {
    Invoke-Step "Formato" { uv run ruff format --check . }
    Invoke-Step "Lint" { uv run ruff check . }
    Invoke-Step "Tipos" { uv run mypy src tests }
    Invoke-Step "Pruebas" { uv run pytest }
    Write-Host "Todas las comprobaciones pasaron." -ForegroundColor Green
}
finally {
    Pop-Location
}

#> Uso
<# cd backend
.\scripts\check.ps1 #>
