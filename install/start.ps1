# Start Accrue: API first (wait until healthy), then UI.
# Login error "API returned empty response" means this API never came up.

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$venvPy = Join-Path $Root ".venv\Scripts\python.exe"

function Wait-Api([int]$seconds = 45) {
    $urls = @("http://127.0.0.1:8000/api/health", "http://localhost:8000/api/health")
    for ($i = 1; $i -le $seconds; $i++) {
        foreach ($url in $urls) {
            try {
                $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 2
                if ($r.StatusCode -eq 200 -and $r.Content -match "ok|degraded") {
                    return $true
                }
            } catch { }
        }
        Start-Sleep -Seconds 1
        Write-Host "  waiting for API... $i/$seconds"
    }
    return $false
}

if (-not (Test-Path $venvPy)) {
    Write-Host "Accrue is not installed. Double-click install\install.bat first." -ForegroundColor Red
    Read-Host "Press Enter to close"
    exit 1
}
if (-not (Test-Path (Join-Path $Root "frontend\node_modules"))) {
    Write-Host "Frontend packages missing. Double-click install\install.bat first." -ForegroundColor Red
    Read-Host "Press Enter to close"
    exit 1
}

$envFile = Join-Path $Root ".env"
if (-not (Test-Path $envFile)) {
    Copy-Item (Join-Path $Root ".env.example") $envFile
}

Write-Host "Starting Accrue from $Root" -ForegroundColor Cyan
Write-Host "1) API window  -> keep open  (port 8000)"
Write-Host "2) UI window   -> keep open  (port 5173)"
Write-Host ""

$apiFile = Join-Path $PSScriptRoot "start-api.ps1"
$webFile = Join-Path $PSScriptRoot "start-web.ps1"

Start-Process powershell -ArgumentList @(
    "-NoExit", "-ExecutionPolicy", "Bypass", "-File", $apiFile
)

Write-Host "Waiting until http://127.0.0.1:8000/api/health responds..."
if (-not (Wait-Api 50)) {
    Write-Host ""
    Write-Host "API did not start. Login will fail with: API returned empty response." -ForegroundColor Red
    Write-Host "Look at the Accrue API window for the Python error (missing package, port in use, etc.)." -ForegroundColor Yellow
    Write-Host "Then run install\start-api.bat by itself, fix the error, and retry." -ForegroundColor Yellow
    Read-Host "Press Enter to close"
    exit 1
}

Write-Host "API is up." -ForegroundColor Green

Start-Process powershell -ArgumentList @(
    "-NoExit", "-ExecutionPolicy", "Bypass", "-File", $webFile
)
Start-Sleep -Seconds 3
Start-Process "http://127.0.0.1:5173"

Write-Host ""
Write-Host "Open:  http://127.0.0.1:5173"
Write-Host "Login: csm@accrue.demo  /  AccrueDemo!2026"
Write-Host "Leave BOTH windows open. If you close the API window, login will fail."
