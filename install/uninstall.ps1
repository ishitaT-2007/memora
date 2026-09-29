# Remove Accrue local install artifacts (does not uninstall Python/Node)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

Write-Host "This deletes .venv, frontend/node_modules, and the SQLite demo database."
$ans = Read-Host "Type YES to continue"
if ($ans -ne "YES") { Write-Host "Cancelled."; exit 0 }

& (Join-Path $PSScriptRoot "stop.ps1")

Remove-Item -Recurse -Force (Join-Path $Root ".venv") -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force (Join-Path $Root "frontend\node_modules") -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force (Join-Path $Root "frontend\dist") -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force (Join-Path $Root ".accrue") -ErrorAction SilentlyContinue
Remove-Item -Force (Join-Path $Root "backend\data\accrue.db") -ErrorAction SilentlyContinue
Write-Host "Local install files removed. Source code and .env were kept."
Write-Host "Reinstall with install\install.bat"
