# Starts only the Accrue UI (port 5173). API must already be running on 8000.

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$frontend = Join-Path $Root "frontend"

function Find-Npm {
    $n = Get-Command npm -ErrorAction SilentlyContinue
    if ($n) { return $n.Source }
    foreach ($dir in @(
        "${env:ProgramFiles}\nodejs",
        "${env:ProgramFiles(x86)}\nodejs",
        "$env:LOCALAPPDATA\Programs\nodejs"
    )) {
        $cmd = Join-Path $dir "npm.cmd"
        if (Test-Path $cmd) { return $cmd }
    }
    return $null
}

if (-not (Test-Path (Join-Path $frontend "node_modules"))) {
    Write-Host "Run install\install.bat first (frontend\node_modules is missing)." -ForegroundColor Red
    Read-Host "Press Enter to close"
    exit 1
}

$npm = Find-Npm
if (-not $npm) {
    Write-Host "npm not found. Install Node.js LTS and reopen this window." -ForegroundColor Red
    Read-Host "Press Enter to close"
    exit 1
}

Set-Location $frontend
Write-Host "Accrue UI"
Write-Host "npm: $npm"
Write-Host "Open http://127.0.0.1:5173 after this says ready."
Write-Host "Do not close this window while using Accrue."
Write-Host ""

& $npm run dev
Write-Host "`nUI process ended."
Read-Host "Press Enter to close"
