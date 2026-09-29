#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
for f in api.pid web.pid; do
  p="$ROOT/.accrue/$f"
  if [ -f "$p" ]; then
    pid="$(cat "$p")"
    kill "$pid" 2>/dev/null || true
    rm -f "$p"
    echo "Stopped $f ($pid)"
  fi
done
# Fallback: ports
for port in 8000 5173; do
  if command -v lsof >/dev/null 2>&1; then
    pids="$(lsof -ti tcp:$port || true)"
    [ -n "$pids" ] && kill $pids 2>/dev/null || true
  fi
done
echo "Done."
