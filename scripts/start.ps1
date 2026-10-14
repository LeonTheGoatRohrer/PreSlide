param([int]$Port = 8000)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $projectRoot
try {
    if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) { throw 'Run scripts/setup.ps1 first.' }
    if (-not (Test-Path -LiteralPath 'data/processed/demo.json')) { throw 'Run the scientific pipeline and python -m preslide.demo first; see README.md.' }
    if (-not (Test-Path -LiteralPath 'frontend/dist/index.html')) {
        Push-Location -LiteralPath (Join-Path $projectRoot 'frontend')
        try {
            npm.cmd run build
            if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
        } finally { Pop-Location }
    }
    Write-Host "PreSlide: http://127.0.0.1:$Port (Ctrl+C to stop)"
    & ./.venv/Scripts/python.exe -m uvicorn preslide.api:app --host 127.0.0.1 --port $Port
} finally { Pop-Location }
