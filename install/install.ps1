# Accrue portable installer
# Run from anywhere:  powershell -ExecutionPolicy Bypass -File install\install.ps1
# Optional:            .\install.ps1 -AddToPath

[CmdletBinding()]
param(
    [switch]$AddToPath,
    [switch]$SkipFrontend
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Write-Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-Ok($msg) { Write-Host "    OK  $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "    !!  $msg" -ForegroundColor Yellow }
function Fail($msg) { Write-Host "    FAIL $msg" -ForegroundColor Red; exit 1 }

function Refresh-SessionPath {
    # New terminals see PATH; this window may have been opened before Python was installed.
    $machine = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $user = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = (@($machine, $user) | Where-Object { $_ }) -join ";"
}

function Test-PythonExe([string]$exe) {
    if (-not $exe) { return $null }
    $exe = $exe.Trim().Trim('"')
    if ($exe -match "WindowsApps") { return $null }
    if (-not (Test-Path -LiteralPath $exe)) { return $null }
    try {
        $ver = & $exe -c "import sys; print('%d.%d' % (sys.version_info.major, sys.version_info.minor))" 2>$null
        if ($LASTEXITCODE -ne 0 -or -not $ver) { return $null }
        $parts = $ver.Trim().Split(".")
        $major = [int]$parts[0]; $minor = [int]$parts[1]
        if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 11)) { return $null }
        return [pscustomobject]@{ Exe = $exe; Args = @(); Version = $ver.Trim(); Dir = (Split-Path $exe) }
    } catch {
        return $null
    }
}

function Resolve-PythonLocation([string]$path, [switch]$SearchNested) {
    $resolved = New-Object System.Collections.Generic.List[string]
    if (-not $path) { return $resolved }
    $path = $path.Trim().Trim('"')
    if (-not $path) { return $resolved }

    if (Test-Path -LiteralPath $path -PathType Leaf) {
        $resolved.Add($path)
        return $resolved
    }

    $folder = $path
    if ($path -match '\.exe$') { $folder = Split-Path $path }
    if (-not $folder -or -not (Test-Path -LiteralPath $folder -PathType Container)) {
        if ($path -match '\.exe$') { $resolved.Add($path) } else { $resolved.Add((Join-Path $path "python.exe")) }
        return $resolved
    }

    $direct = Join-Path $folder "python.exe"
    if (Test-Path -LiteralPath $direct -PathType Leaf) {
        $resolved.Add($direct)
        return $resolved
    }

    if ($SearchNested) {
        Get-ChildItem -LiteralPath $folder -Filter python.exe -File -Recurse -Depth 3 -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -notmatch '\\(\.venv|venv|node_modules|__pycache__)\\' } |
            ForEach-Object { $resolved.Add($_.FullName) }
    } else {
        $resolved.Add($direct)
    }
    return $resolved
}

function Add-Candidate([System.Collections.Generic.List[string]]$list, [string]$path) {
    if (-not $path) { return }
    foreach ($exe in (Resolve-PythonLocation $path)) {
        if ($exe) { $list.Add($exe) }
    }
}

function Add-PortablePythonHome([System.Collections.Generic.List[string]]$list, [string]$folder) {
    if (-not $folder) { return }
    foreach ($exe in (Resolve-PythonLocation $folder -SearchNested)) {
        if ($exe) { $list.Add($exe) }
    }
}

function Get-PythonFromRegistry {
    $found = New-Object System.Collections.Generic.List[string]
    $roots = @(
        "HKCU:\Software\Python\PythonCore",
        "HKLM:\Software\Python\PythonCore",
        "HKLM:\Software\Wow6432Node\Python\PythonCore"
    )
    foreach ($root in $roots) {
        if (-not (Test-Path $root)) { continue }
        Get-ChildItem $root -ErrorAction SilentlyContinue | ForEach-Object {
            $installKey = Join-Path $_.PSPath "InstallPath"
            if (-not (Test-Path $installKey)) { return }
            $key = Get-Item $installKey -ErrorAction SilentlyContinue
            if (-not $key) { return }
            $exePath = $key.GetValue("ExecutablePath")
            if ($exePath) { Add-Candidate $found "$exePath" }
            $home = $key.GetValue("")
            if ($home) { Add-Candidate $found (Join-Path "$home" "python.exe") }
        }
    }
    return $found
}

function Find-Python {
    Refresh-SessionPath
    $candidates = New-Object System.Collections.Generic.List[string]

    if ($env:ACCRUE_PYTHON) {
        foreach ($exe in (Resolve-PythonLocation $env:ACCRUE_PYTHON -SearchNested)) {
            $forced = Test-PythonExe $exe
            if ($forced) {
                Write-Host "    Using ACCRUE_PYTHON: $($forced.Exe)  (Python $($forced.Version))"
                return $forced
            }
        }
        Write-Warn "ACCRUE_PYTHON is set but is not a working Python 3.11+: $env:ACCRUE_PYTHON"
    }

    # Portable / copied Python (other PC: E:\ishtapython)
    Add-PortablePythonHome $candidates "E:\ishtapython"
    Get-PSDrive -PSProvider FileSystem -ErrorAction SilentlyContinue | ForEach-Object {
        Add-PortablePythonHome $candidates (Join-Path $_.Root "ishtapython")
    }
    Add-PortablePythonHome $candidates (Join-Path $Root "ishtapython")
    Add-PortablePythonHome $candidates (Join-Path $Root "python")

    foreach ($p in (Get-PythonFromRegistry)) { Add-Candidate $candidates $p }

    $globs = @(
        "$env:LOCALAPPDATA\Programs\Python\Python*\python.exe",
        "${env:ProgramFiles}\Python*\python.exe",
        "${env:ProgramFiles(x86)}\Python*\python.exe",
        "C:\Python*\python.exe",
        "$env:USERPROFILE\miniconda3\python.exe",
        "$env:USERPROFILE\anaconda3\python.exe",
        "$env:LOCALAPPDATA\miniconda3\python.exe",
        "$env:USERPROFILE\.pyenv\pyenv-win\versions\*\python.exe"
    )
    foreach ($g in $globs) {
        Get-Item -Path $g -ErrorAction SilentlyContinue | ForEach-Object {
            Add-Candidate $candidates $_.FullName
        }
    }

    if (Get-Command py -ErrorAction SilentlyContinue) {
        $list = & py -0p 2>$null
        foreach ($line in @($list)) {
            if ($line -match '([A-Za-z]:\\[^\r\n]*python\.exe)') {
                Add-Candidate $candidates $Matches[1]
            }
        }
        foreach ($tag in @("-3.12", "-3.11", "-3.13", "-3.14", "-3")) {
            try {
                $home = & py $tag -c "import sys; print(sys.executable)" 2>$null
                if ($LASTEXITCODE -eq 0 -and $home) { Add-Candidate $candidates $home }
            } catch { }
        }
    }

    try {
        foreach ($w in @(& where.exe python 2>$null)) {
            if ($w -and $w -notmatch "WindowsApps") { Add-Candidate $candidates $w }
        }
        foreach ($w in @(& where.exe python3 2>$null)) {
            if ($w -and $w -notmatch "WindowsApps") { Add-Candidate $candidates $w }
        }
    } catch { }

    foreach ($name in @("python", "python3")) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if ($cmd -and $cmd.Source -and $cmd.Source -notmatch "WindowsApps") {
            Add-Candidate $candidates $cmd.Source
        }
    }

    $seen = @{}
    $working = New-Object System.Collections.Generic.List[object]
    foreach ($path in $candidates) {
        $key = $path.ToLowerInvariant()
        if ($seen.ContainsKey($key)) { continue }
        $seen[$key] = $true
        $hit = Test-PythonExe $path
        if ($hit) { $working.Add($hit) }
    }

    if ($working.Count -eq 0) { return $null }

    $ranked = @($working) | Sort-Object -Property @{
        Expression = {
            $min = [int]($_.Version.Split(".")[1])
            $score = switch ($min) { 12 { 100 }; 11 { 90 }; 13 { 80 }; 14 { 70 }; default { 40 + $min } }
            if ($_.Exe -match "miniconda|anaconda") { $score -= 5 }
            if ($_.Exe -match '(?i)[\\/]ishtapython([\\/]|$)') { $score += 50 }
            $score
        }
        Descending = $true
    }
    $best = $ranked[0]

    Write-Host "    Found Python on this PC:"
    foreach ($hit in $working) {
        $mark = ""
        if ($hit.Exe -eq $best.Exe) { $mark = "  <- using this" }
        Write-Host ("      {0,-6} {1}{2}" -f $hit.Version, $hit.Exe, $mark)
    }
    return $best
}

function Test-Venv([string]$venvPy) {
    if (-not (Test-Path -LiteralPath $venvPy)) { return $false }
    $venvRoot = Split-Path (Split-Path $venvPy)
    $cfg = Join-Path $venvRoot "pyvenv.cfg"
    if (Test-Path -LiteralPath $cfg) {
        foreach ($line in Get-Content -LiteralPath $cfg) {
            if ($line -match '^\s*(home|executable)\s*=\s*(.+)\s*$') {
                $val = $Matches[2].Trim().Trim('"')
                if ($Matches[1] -eq "home") {
                    $homePy = Join-Path $val "python.exe"
                    if (-not (Test-Path -LiteralPath $val) -and -not (Test-Path -LiteralPath $homePy)) {
                        return $false
                    }
                } elseif ($val -and -not (Test-Path -LiteralPath $val)) {
                    return $false
                }
            }
        }
    }
    try {
        $out = & $venvPy -c "print('ok')" 2>&1 | Out-String
        if ($LASTEXITCODE -ne 0) { return $false }
        if ($out -match "cannot find the path specified" -or $out -match "did not find executable") { return $false }
        return ($out -match "ok")
    } catch {
        return $false
    }
}

function Find-Node {
    $n = Get-Command node -ErrorAction SilentlyContinue
    $m = Get-Command npm -ErrorAction SilentlyContinue
    if ($n -and $m) {
        $ver = (& node -v).Trim()
        return @{ Node = $n.Source; Npm = $m.Source; Version = $ver; Dir = Split-Path $n.Source }
    }
    $guesses = @(
        "${env:ProgramFiles}\nodejs",
        "${env:ProgramFiles(x86)}\nodejs",
        "$env:LOCALAPPDATA\Programs\nodejs"
    )
    foreach ($dir in $guesses) {
        if (Test-Path "$dir\node.exe") {
            return @{
                Node = "$dir\node.exe"
                Npm = "$dir\npm.cmd"
                Version = (& "$dir\node.exe" -v).Trim()
                Dir = $dir
            }
        }
    }
    return $null
}

function Add-UserPath([string]$dir) {
    if (-not (Test-Path $dir)) { return }
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($null -eq $userPath) { $userPath = "" }
    $parts = $userPath -split ";" | Where-Object { $_ -and $_.Trim() }
    if ($parts -contains $dir) {
        Write-Ok "Already on User PATH: $dir"
        return
    }
    $new = ($parts + $dir) -join ";"
    [Environment]::SetEnvironmentVariable("Path", $new, "User")
    $env:Path = $dir + ";" + $env:Path
    Write-Ok "Added to User PATH: $dir"
}

Write-Host "Accrue installer" -ForegroundColor White
Write-Host "Project root: $Root"

Write-Step "Checking Python 3.11+"
$py = Find-Python
if (-not $py) {
    Fail @"
Python 3.11+ was not found on this PC (the installer looks it up for you — you do not type a path).

See every installed copy:
  py -0p
  where.exe python

This installer also looks in E:\ishtapython (folder or python.exe inside it).

If you know python.exe exists, point the installer at it and retry:
  set ACCRUE_PYTHON=E:\ishtapython
  install\install.bat

Otherwise install Python 3.12 from https://www.python.org/downloads/
On the first screen, CHECK: Add python.exe to PATH
Then close this window and run install\install.bat again.
"@
}
$major, $minor = $py.Version.Split(".")
if ([int]$major -lt 3 -or ([int]$major -eq 3 -and [int]$minor -lt 11)) {
    Fail "Python $($py.Version) is too old. Accrue needs 3.11+"
}
Write-Ok "Python $($py.Version)  ($($py.Exe))"

Write-Step "Checking Node.js 18+"
$node = Find-Node
if (-not $node) {
    Fail @"
Node.js was not found.
Install the LTS build from https://nodejs.org/
The Node installer adds Node to PATH automatically.
Close this window and run install\install.bat again.
"@
}
$nver = $node.Version.TrimStart("v").Split(".")[0]
if ([int]$nver -lt 18) {
    Fail "Node $($node.Version) is too old. Accrue needs 18+"
}
Write-Ok "Node $($node.Version)  ($($node.Node))"

if ($AddToPath) {
    Write-Step "Updating User PATH"
    Add-UserPath $py.Dir
    if ($py.Dir -notmatch "WindowsApps") { Add-UserPath (Join-Path $py.Dir "Scripts") }
    Add-UserPath $node.Dir
    [Environment]::SetEnvironmentVariable("ACCRUE_HOME", $Root, "User")
    Write-Ok "ACCRUE_HOME=$Root"
}

Write-Step "Environment file"
if (-not (Test-Path "$Root\.env")) {
    Copy-Item "$Root\.env.example" "$Root\.env"
    Write-Ok "Created .env from .env.example"
} else {
    Write-Ok ".env already exists (left unchanged)"
}

Write-Step "Python virtual environment"
$venvPy = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Venv $venvPy)) {
    if (Test-Path (Join-Path $Root ".venv")) {
        Write-Warn "Existing .venv is broken (base Python was moved or uninstalled). Recreating it."
        Remove-Item -Recurse -Force (Join-Path $Root ".venv")
    }
    Write-Host "    Using $($py.Exe) (Python $($py.Version))"
    & $py.Exe -m venv "$Root\.venv"
    if ($LASTEXITCODE -ne 0 -or -not (Test-Venv $venvPy)) {
        Fail "venv creation failed using $($py.Exe). Delete the .venv folder and run install.bat again, or set ACCRUE_PYTHON to that python.exe path."
    }
    Write-Ok "Created .venv"
} else {
    Write-Ok ".venv is valid"
}

Write-Step "Python packages"
$pyMinor = [int]$py.Version.Split(".")[1]
if ($pyMinor -ge 14) {
    Write-Warn "Python $($py.Version) is new. Accrue will install packages that already have Windows wheels (no Visual Studio / Rust compile)."
}
& $venvPy -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { Fail "pip upgrade failed (venv Python is not working)" }

$reqFile = Join-Path $Root "backend\requirements.txt"
$raw = Get-Content -LiteralPath $reqFile
$core = New-Object System.Collections.Generic.List[string]
$wantPostgres = $false
$flex = @{
    "fastapi"            = "fastapi>=0.115.12,<0.129"
    "pydantic"           = "pydantic>=2.11.3,<3"
    "pydantic-settings"  = "pydantic-settings>=2.8.1,<3"
    "sqlalchemy"         = "sqlalchemy>=2.0.40,<2.1"
    "httpx"              = "httpx>=0.28.1,<0.29"
    "python-multipart"   = "python-multipart>=0.0.20,<1"
    "python-jose"        = "python-jose[cryptography]>=3.4.0,<4"
    "bcrypt"             = "bcrypt>=4.2.1,<5"
    "email-validator"    = "email-validator>=2.2.0,<3"
    "pytest"             = "pytest>=8.3.5,<9"
    "pytest-asyncio"     = "pytest-asyncio>=0.26.0,<2"
}
foreach ($line in $raw) {
    $t = $line.Trim()
    if (-not $t -or $t.StartsWith("#")) {
        $core.Add($line)
        continue
    }
    if ($t -match '^\s*psycopg') {
        $wantPostgres = $true
        Write-Warn "Skipping '$t' (optional PostgreSQL driver; SQLite is the default)"
        continue
    }
    $pkg = ($t -split '[<>=\[!~; ]')[0].ToLower()
    if ($pkg -eq "uvicorn") {
        if ($pyMinor -ge 14) {
            $core.Add("uvicorn>=0.34.2,<0.41")
            Write-Warn "Python 3.14: installing uvicorn without compiled extras (watchfiles/httptools)"
        } else {
            $core.Add("uvicorn[standard]>=0.34.2,<0.41")
        }
        continue
    }
    if ($flex.ContainsKey($pkg)) {
        if ($t -ne $flex[$pkg]) { Write-Host "    Using $($flex[$pkg])  (was $t)" }
        $core.Add($flex[$pkg])
        continue
    }
    $core.Add($line)
}
$coreFile = Join-Path $env:TEMP "accrue-requirements-core.txt"
$core | Set-Content -LiteralPath $coreFile -Encoding ascii
try {
    Write-Host "    pip install --only-binary pydantic-core,watchfiles,httptools"
    & $venvPy -m pip install --prefer-binary --only-binary "pydantic-core,watchfiles,httptools" -r $coreFile
    if ($LASTEXITCODE -ne 0) { Fail "pip install failed" }
} finally {
    Remove-Item -LiteralPath $coreFile -ErrorAction SilentlyContinue
}

$pgSpec = "psycopg[binary]>=3.2.10,<4"
$pgFile = Join-Path $Root "backend\requirements-postgres.txt"
if (Test-Path -LiteralPath $pgFile) {
    $pgLine = Get-Content -LiteralPath $pgFile | Where-Object { $_ -match '^\s*psycopg' } | Select-Object -First 1
    if ($pgLine) { $pgSpec = $pgLine.Trim() }
}
if ($wantPostgres -or (Test-Path -LiteralPath $pgFile)) {
    Write-Host "    Optional PostgreSQL driver: $pgSpec"
    & $venvPy -m pip install $pgSpec
    if ($LASTEXITCODE -ne 0) {
        Write-Warn "PostgreSQL driver not installed (this Python has no matching wheel). Accrue will use SQLite."
    } else {
        Write-Ok "PostgreSQL driver installed"
    }
}
Write-Ok "Python packages installed"

Write-Step "Data directory"
New-Item -ItemType Directory -Force -Path "$Root\backend\data" | Out-Null
Write-Ok "backend\data"

if (-not $SkipFrontend) {
    Write-Step "Frontend packages (npm install)"
    Push-Location "$Root\frontend"
    try {
        & $node.Npm install
        if ($LASTEXITCODE -ne 0) { Fail "npm install failed" }
        Write-Ok "frontend/node_modules ready"
    } finally {
        Pop-Location
    }
}

$marker = Join-Path $Root ".accrue"
New-Item -ItemType Directory -Force -Path $marker | Out-Null
@"
installed=$(Get-Date -Format o)
root=$Root
python=$venvPy
node=$($node.Node)
"@ | Set-Content (Join-Path $marker "install-info.txt") -Encoding UTF8

Write-Host "`nInstall complete." -ForegroundColor Green
Write-Host @"

Start Accrue:
  double-click  install\start.bat
  or            powershell -ExecutionPolicy Bypass -File install\start.ps1

Open:  http://127.0.0.1:5173
Login: csm@accrue.demo  /  AccrueDemo!2026

Full guide: docs\INSTALLATION_GUIDE.md
"@
