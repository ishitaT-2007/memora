# Create Accrue-Portable.zip for copying to another PC (no venv / node_modules).

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Out = Join-Path $Root "Accrue-Portable.zip"
if (Test-Path $Out) { Remove-Item $Out -Force }

$exclude = @(
    "\.venv\\",
    "\\node_modules\\",
    "\\.git\\",
    "\\__pycache__\\",
    "\\.pytest_cache\\",
    "\\frontend\\dist\\",
    "\\frontend\\.vite\\",
    "Accrue-Portable.zip"
)

$files = Get-ChildItem -Path $Root -Recurse -File | Where-Object {
    $p = $_.FullName
    foreach ($e in $exclude) {
        if ($p -match $e) { return $false }
    }
    if ($_.Name -eq "accrue.db") { return $false }
    if ($_.Extension -eq ".pyc") { return $false }
    return $true
}

$temp = Join-Path $env:TEMP ("accrue-pack-" + [guid]::NewGuid().ToString("n"))
New-Item -ItemType Directory -Path $temp | Out-Null
try {
    foreach ($f in $files) {
        $rel = $f.FullName.Substring($Root.Length).TrimStart("\", "/")
        $dest = Join-Path $temp $rel
        $destDir = Split-Path $dest
        if (-not (Test-Path $destDir)) { New-Item -ItemType Directory -Force -Path $destDir | Out-Null }
        Copy-Item $f.FullName $dest
    }
    Copy-Item (Join-Path $Root "docs\INSTALLATION_GUIDE.md") (Join-Path $temp "START_HERE.md") -ErrorAction SilentlyContinue
    Compress-Archive -Path (Join-Path $temp "*") -DestinationPath $Out -Force
    Write-Host "Created $Out"
    Write-Host "Copy that zip to the other PC, extract, then run install\install.bat"
} finally {
    Remove-Item -Recurse -Force $temp -ErrorAction SilentlyContinue
}
