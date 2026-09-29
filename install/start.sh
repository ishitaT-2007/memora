#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/.venv/bin/python"
[ -x "$PY" ] || { echo "Run bash install/install.sh first."; exit 1; }
[ -d "$ROOT/frontend/node_modules" ] || { echo "Run bash install/install.sh first."; exit 1; }
[ -f "$ROOT/.env" ] || cp "$ROOT/.env.example" "$ROOT/.env"

mkdir -p "$ROOT/.accrue"
echo "Starting Accrue API on :8000 and UI on :5173"

(
  cd "$ROOT/backend"
  export PYTHONPATH="$ROOT/backend"
  exec "$PY" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
) &
echo $! > "$ROOT/.accrue/api.pid"

(
  cd "$ROOT/frontend"
  exec npm run dev
) &
echo $! > "$ROOT/.accrue/web.pid"

sleep 3
echo "UI  http://127.0.0.1:5173"
echo "API http://127.0.0.1:8000/docs"
echo "Login: csm@accrue.demo / AccrueDemo!2026"
echo "Stop with: bash install/stop.sh"
command -v xdg-open >/dev/null && xdg-open "http://127.0.0.1:5173" || true
command -v open >/dev/null && open "http://127.0.0.1:5173" || true
wait
