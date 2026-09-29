# Accrue

**Live Account Rescue Agent** — a Hindsight-powered copilot for Customer Success Managers handling urgent B2B escalations.

A CSM pastes an angry email or incident note. Accrue retrieves approved account memory, comparable save/churn outcomes, and team corrections; then returns a 20-second brief, evidence-linked Do/Don’t, and an **unsent** editable draft. Corrections are previewed, scoped, and saved so the next matching crisis is smarter.

This repository implements the full MVP in [Accrue_Two_Person_Development_Plan.docx](./Accrue_Two_Person_Development_Plan.docx) (Weeks 1–8). All customer records in the demo corpus are **synthetic**.

---

## What is in the MVP

| Capability | Status |
|---|---|
| Paste escalation + account confirmation (FR-01, FR-02) | Done |
| Retrieve customer context and comparable outcomes (FR-03, FR-04) | Done |
| 20-second brief, Do/Don’t, editable draft (FR-05–FR-07) | Done |
| Correction preview → confirm → recall (FR-08) | Done |
| Source details (FR-09) | Done |
| Audit history (FR-10) | Done (admin) |
| Copy/export (FR-11) | Done |
| Multi-tenant productization (FR-12) | Post-MVP |

**Not in V1:** CRM/Slack/PagerDuty, autonomous sending, credits, or churn models.

---

## Install on another computer

Full step-by-step (Python/Node PATH, zip copy, Windows `.bat` installer, macOS/Linux): **[docs/INSTALLATION_GUIDE.md](docs/INSTALLATION_GUIDE.md)**

On the **source** PC, build a transfer zip:

```powershell
install\package-for-transfer.bat
```

On the **new** PC, extract the zip, then double-click `install\install.bat` and `install\start.bat`. Open http://127.0.0.1:5173

## Quick start (this machine)

You need Python 3.11+ and Node 18+. PostgreSQL is optional; SQLite is the default.

```powershell
cd c:\xampp\htdocs\ishita
copy .env.example .env

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt

# API  → http://127.0.0.1:8000/docs
cd backend
$env:PYTHONPATH = "."
uvicorn app.main:app --reload --port 8000
```

In a second terminal:

```powershell
cd c:\xampp\htdocs\ishita\frontend
npm install
npm run dev
```

Open **http://localhost:5173**

| Role | Email | Password |
|---|---|---|
| CSM | `csm@accrue.demo` | `AccrueDemo!2026` |
| Admin | `admin@accrue.demo` | `AccrueAdmin!2026` |

---

## 60-second demo

1. Sign in as CSM. Acme Cloud is preselected ($180,000 ARR).
2. Click **Run 60s demo**. The Acme email loads and the brief appears on the right.
3. Show the brief: March reliability threat, dedicated updates, Q2 SSO slipped.
4. Show comparable **save** (Northstar: founder note + 48-hour war room) vs **churn** (Helix: credits without a fix).
5. Open source IDs. Toggle **Memory off** and Analyze again — history disappears.
6. Save correction: *Never offer credits to Priya; escalate to engineering first.*
7. Analyze again — the correction is retrieved.
8. Copy the draft. Accrue never sends it.

Full script: [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md).

---

## How Hindsight memory is used

Accrue never asks the model to invent account history.

1. **Retain** curated facts, landmines, commitments, incidents, and playbooks into a per-account memory bank (plus comparable playbooks).
2. **Recall** on each Analyze, scoped to the selected account; comparable `scope=comparable` memories may be retrieved as playbooks, not as another customer’s private CRM.
3. **Generate** a strict JSON brief from that context pack only.
4. **Validate** source IDs; drop uncited claims; strip prompt-injection promises.
5. **Correct** via preview/confirm. Historical source records are not overwritten.

Default `HINDSIGHT_MODE=mock` is a faithful retain/recall adapter so the product runs without a live cluster. Point `HINDSIGHT_MODE=hindsight` + `HINDSIGHT_BASE_URL` at [Hindsight](https://hindsight.vectorize.io/) when ready. LLM defaults to a grounded mock; set `LLM_MODE=groq` and `GROQ_API_KEY` for live generation.

---

## Tests

```powershell
cd c:\xampp\htdocs\ishita\backend
$env:PYTHONPATH = "."
pytest -q
```

Golden 10-scenario replay (API must be up):

```powershell
cd c:\xampp\htdocs\ishita
$env:PYTHONPATH = "backend"
python scripts\run_golden_scenarios.py
```

Reset demo data:

```powershell
$env:PYTHONPATH = "backend"
python scripts\reset_demo.py
```

Admin users can also hit **Reset demo data** in the UI.

---

## Docker (staging-shaped)

```powershell
docker compose up --build
```

Web: http://localhost:8080 · API: http://localhost:8000

---

## Repository map

```
backend/app          FastAPI, schema, orchestration, adapters
backend/tests        API, grounding, correction, security tests
frontend/src        Single-screen CSM workflow
docs/               Runbook, retention, release, post-MVP
scripts/            Seed reset + golden scenarios
```

---

## Docs

- [Runbook](docs/RUNBOOK.md)
- [Release checklist](docs/RELEASE_CHECKLIST.md)
- [Data retention](docs/DATA_RETENTION.md)
- [Demo script](docs/DEMO_SCRIPT.md)
- [Post-MVP backlog](docs/POST_MVP_BACKLOG.md)
- [Hindsight usage](docs/HINDSIGHT_USAGE.md)
