# Starts only the Accrue API (port 8000). Leave this window open.

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$venvPy = Join-Path $Root ".venv\Scripts\python.exe"
$logDir = Join-Path $Root ".accrue"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

if (-not (Test-Path $venvPy)) {
    Write-Host "Run install\install.bat first (.venv is missing)." -ForegroundColor Red
    Read-Host "Press Enter to close"
    exit 1
}

$hostName = "0.0.0.0"
$port = 8000
$env:PYTHONPATH = Join-Path $Root "backend"
Set-Location (Join-Path $Root "backend")

Write-Host "Accrue API"
Write-Host "Root: $Root"
Write-Host "Python: $venvPy"
Write-Host "PYTHONPATH: $env:PYTHONPATH"
Write-Host "Listen: http://127.0.0.1:$port  (all interfaces $hostName)"
Write-Host "Health: http://127.0.0.1:$port/api/health"
Write-Host "Do not close this window while using Accrue."
Write-Host ""

& $venvPy -m uvicorn app.main:app --host $hostName --port $port --reload
$code = $LASTEXITCODE
Write-Host "`nAPI exited with code $code" -ForegroundColor Red
Write-Host "If this closed immediately, copy the error above."
Read-Host "Press Enter to close"
exit $code
