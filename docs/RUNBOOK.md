# Accrue runbook

Install on a new PC: **[INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md)** (`install\install.bat` then `install\start.bat`).

## Local start

1. Copy `.env.example` to `.env`.
2. Create venv, install `backend/requirements.txt`.
3. From `backend/`: `PYTHONPATH=. uvicorn app.main:app --reload --port 8000`.
4. From `frontend/`: `npm install && npm run dev`.
5. Open http://localhost:5173.

First boot creates SQLite at `backend/data/accrue.db` and seeds synthetic accounts.

## Health

`GET /api/health` reports database, Hindsight adapter, and LLM adapter. `degraded` means the UI should still load; Analyze may run memory-limited.

## Demo reset

- UI (admin): **Reset demo data**
- CLI: `PYTHONPATH=backend python scripts/reset_demo.py`
- This deletes escalations, corrections, and memories, then restores the synthetic corpus.

## Credentials

Change demo passwords in `.env` before any shared staging URL. Staging must keep authentication on.

## Provider failover

| Mode | When |
|---|---|
| `HINDSIGHT_MODE=mock` | Default. Local retain/recall JSON store. |
| `HINDSIGHT_MODE=hindsight` | Live server at `HINDSIGHT_BASE_URL`. |
| `LLM_MODE=mock` | Default. Grounded deterministic generator. |
| `LLM_MODE=groq` | Live Groq model; falls back to mock on error. |

## Backup / restore (SQLite)

Backup: copy `backend/data/accrue.db`.
Restore: stop API, replace the file, start API.
Postgres: `pg_dump` / `pg_restore` against `DATABASE_URL`.

## Logging

Request IDs are returned as `X-Request-ID`. Audit rows store actor, action, object, and memory IDs. Full customer emails are stored only if `RETAIN_RAW_INPUT=true` (default for demo). Set false before real data.

## Common failures

| Symptom | Check |
|---|---|
| 401 on API | Token expired; sign in again |
| ACCOUNT_FORBIDDEN | User lacks `account_access` |
| RATE_LIMITED | 30 analyzes / user / minute |
| Generic brief | Memory limited or Hindsight down |
| bcrypt errors | Reinstall `passlib[bcrypt]` and `bcrypt==4.2.1` |
