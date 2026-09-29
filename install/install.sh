#!/usr/bin/env bash
# Accrue installer for macOS and Linux
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

step() { printf '\n==> %s\n' "$1"; }
ok() { printf '    OK  %s\n' "$1"; }
fail() { printf '    FAIL %s\n' "$1" >&2; exit 1; }

step "Checking Python 3.11+"
if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  fail "Python 3.11+ not found. Install from https://www.python.org/downloads/ or your package manager."
fi
VER="$($PY -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
MAJ="${VER%%.*}"; MIN="${VER#*.}"
if [ "$MAJ" -lt 3 ] || { [ "$MAJ" -eq 3 ] && [ "$MIN" -lt 11 ]; }; then
  fail "Python $VER is too old (need 3.11+)"
fi
ok "Python $VER ($PY)"

step "Checking Node.js 18+"
command -v node >/dev/null 2>&1 || fail "Node.js not found. Install LTS from https://nodejs.org/"
command -v npm >/dev/null 2>&1 || fail "npm not found. Reinstall Node.js LTS."
NVER="$(node -v | tr -d 'v' | cut -d. -f1)"
[ "$NVER" -ge 18 ] || fail "Node $(node -v) is too old (need 18+)"
ok "Node $(node -v)"

step "Environment file"
if [ ! -f "$ROOT/.env" ]; then
  cp "$ROOT/.env.example" "$ROOT/.env"
  ok "Created .env"
else
  ok ".env already exists"
fi

step "Python virtual environment"
if ! "$ROOT/.venv/bin/python" -c "print('ok')" >/dev/null 2>&1; then
  rm -rf "$ROOT/.venv"
  "$PY" -m venv "$ROOT/.venv"
  ok "Created .venv"
else
  ok ".venv is valid"
fi

step "Python packages"
"$ROOT/.venv/bin/python" -m pip install --upgrade pip
"$ROOT/.venv/bin/python" -m pip install -r "$ROOT/backend/requirements.txt"
ok "requirements installed"

mkdir -p "$ROOT/backend/data"
ok "backend/data"

step "Frontend packages"
( cd "$ROOT/frontend" && npm install )
ok "node_modules ready"

mkdir -p "$ROOT/.accrue"
cat > "$ROOT/.accrue/install-info.txt" <<EOF
installed=$(date -Iseconds)
root=$ROOT
python=$ROOT/.venv/bin/python
EOF

printf '\nInstall complete.\nStart with:  bash install/start.sh\nOpen: http://127.0.0.1:5173\nLogin: csm@accrue.demo / AccrueDemo!2026\nGuide: docs/INSTALLATION_GUIDE.md\n'
