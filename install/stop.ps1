# Stop Accrue processes bound to 8000 and 5173 (Windows)

$ports = 8000, 5173
foreach ($port in $ports) {
    $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    foreach ($c in $conns) {
        if ($c.OwningProcess) {
            Write-Host "Stopping PID $($c.OwningProcess) on port $port"
            Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue
        }
    }
}
Write-Host "Done. You can close leftover Accrue terminal windows."
