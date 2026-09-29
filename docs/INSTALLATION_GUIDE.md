# Accrue — complete installation guide

Use this document to install Accrue on **any Windows, macOS, or Linux machine**. You do not need XAMPP. The copy that lives under `c:\xampp\htdocs\ishita` is only the development folder on the original PC.

**After a successful install you will have:**

| Service | URL |
|---|---|
| Web UI | http://127.0.0.1:5173 |
| API + docs | http://127.0.0.1:8000/docs |
| Health | http://127.0.0.1:8000/api/health |

**Demo login (synthetic data only)**

| Role | Email | Password |
|---|---|---|
| CSM | `csm@accrue.demo` | `AccrueDemo!2026` |
| Admin | `admin@accrue.demo` | `AccrueAdmin!2026` |

---

## 1. What the other computer needs

### Hardware

- 8 GB RAM recommended (4 GB can work)
- ~1.5 GB free disk after Python + Node + `node_modules` + `.venv`
- Ports **5173** (UI) and **8000** (API) must be free

### Operating systems

- Windows 10 or 11 (64-bit)
- macOS 12+
- Ubuntu 22.04+ or similar Linux

### Software you must install first (once per machine)

| Tool | Version | Why |
|---|---|---|
| Python | **3.11 or 3.12** (3.13 works) | Backend (FastAPI) |
| Node.js | **18 LTS or 20 LTS** | Frontend (Vite + React) |
| npm | Comes with Node | Installs frontend packages |

Optional:

| Tool | When |
|---|---|
| Git | If you clone the repo instead of copying a zip |
| Docker Desktop | If you prefer `docker compose up` instead of Python/Node |
| PostgreSQL 16 | Only if you change `DATABASE_URL`; default is SQLite |

You do **not** need Apache, PHP, or XAMPP on the new PC.

---

## 2. PATH settings (read this before installing Python/Node)

PATH is the list of folders Windows/macOS/Linux search when you type `python` or `node`. If PATH is wrong, the Accrue installer will say Python or Node was not found.

### Windows 11 / 10 — Python PATH

1. Download the Windows installer: https://www.python.org/downloads/
2. Run it.
3. On the **first screen**, tick **Add python.exe to PATH**.
4. Click **Install Now** (or Customize and keep the PATH box checked).
5. Close **all** Command Prompt / PowerShell / Cursor terminals, then open a **new** one.
6. Check:

```powershell
py -3 --version
python --version
where.exe python
where.exe py
```

You want a version **3.11 or newer**, and a path similar to:

- `C:\Users\<you>\AppData\Local\Programs\Python\Python312\python.exe`
- or `C:\Python312\python.exe`

If `python` opens the Microsoft Store instead of Python:

1. Settings → Apps → Advanced app settings → App execution aliases
2. Turn **off** `python.exe` and `python3.exe` aliases
3. Reinstall Python with **Add to PATH** checked

**Manual PATH (only if you skipped the checkbox):**

1. Find the folder that contains `python.exe` (example: `C:\Users\sunny\AppData\Local\Programs\Python\Python312`)
2. Also note the `Scripts` folder beside it (`...\Python312\Scripts`)
3. Settings → System → About → Advanced system settings → **Environment Variables**
4. Under **User variables**, select **Path** → Edit → New
5. Add both folders, for example:
   - `C:\Users\<you>\AppData\Local\Programs\Python\Python312`
   - `C:\Users\<you>\AppData\Local\Programs\Python\Python312\Scripts`
6. OK on all dialogs. **Open a new terminal.**

The Accrue installer can do this for you:

```powershell
powershell -ExecutionPolicy Bypass -File install\install.ps1 -AddToPath
```

That appends the detected Python and Node folders to **your User PATH** and sets `ACCRUE_HOME` to the project folder. It does not overwrite the rest of PATH.

### Windows — Node.js PATH

1. Download **LTS**: https://nodejs.org/
2. Run the `.msi`. Leave **Add to PATH** enabled (default).
3. New terminal:

```powershell
node -v
npm -v
where.exe node
```

Typical path: `C:\Program Files\nodejs\`

If `node` is not found, add `C:\Program Files\nodejs\` to User PATH the same way as Python.

### macOS — PATH

Install Python 3.12 from python.org **or**:

```bash
brew install python@3.12 node
```

Homebrew already puts them on PATH (`/opt/homebrew/bin` on Apple Silicon, `/usr/local/bin` on Intel). Confirm:

```bash
python3 --version
node -v
echo $PATH
```

If `python3` is missing after a python.org install, add (zsh):

```bash
echo 'export PATH="$HOME/Library/Python/3.12/bin:/Library/Frameworks/Python.framework/Versions/3.12/bin:$PATH"' >> ~/.zprofile
source ~/.zprofile
```

### Linux (Ubuntu/Debian) — PATH

```bash
sudo apt update
sudo apt install python3.12 python3.12-venv python3-pip
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
python3 --version
node -v
```

System packages land on `/usr/bin`, which is already on PATH.

---

## 3. Copy Accrue onto the new computer

Pick **one** method.

### Method A — zip from the original PC (simplest)

On the **source** machine, in the Accrue folder:

```powershell
powershell -ExecutionPolicy Bypass -File install\package-for-transfer.ps1
```

That creates `Accrue-Portable.zip` **without** `.venv` or `node_modules` (those must be rebuilt on the new PC).

On the **target** PC:

1. Copy the zip (USB, OneDrive, email, shared drive).
2. Extract to a folder **without spaces if possible**, for example:
   - `C:\Accrue`
   - `D:\apps\accrue`
   - `C:\Users\<you>\Documents\Accrue`
3. Do **not** extract into a path so long that Windows hits the 260-character limit (deep `node_modules` trees).

### Method B — copy the whole folder

Copy the project directory, but you can skip:

- `.venv`
- `frontend\node_modules`
- `backend\data\accrue.db`
- `__pycache__`

The installer recreates those.

### Method C — Git

```powershell
git clone <your-repo-url> Accrue
cd Accrue
```

---

## 4. Windows: install Accrue (one command)

1. Open the extracted folder.
2. Double-click:

```
install\install.bat
```

If Windows blocks scripts, right-click `install.bat` → Run as administrator is **not** required. Instead open PowerShell **in that folder**:

```powershell
cd C:\Accrue
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\install\install.ps1
```

Optional PATH helper (once per user account):

```powershell
.\install\install.ps1 -AddToPath
```

Then **close and reopen** the terminal so PATH updates apply.

The installer will:

1. Check Python 3.11+ and Node 18+
2. Copy `.env.example` → `.env` if `.env` is missing
3. Create `.venv`
4. `pip install -r backend\requirements.txt`
5. Create `backend\data`
6. `npm install` in `frontend`

### Start Accrue (Windows)

Double-click:

```
install\start.bat
```

Two PowerShell windows open (API + UI). A browser tab should open to **http://127.0.0.1:5173**.

Leave both windows open while you use the app.

### Stop Accrue (Windows)

```
install\stop.bat
```

Or close the two terminal windows.

---

## 5. macOS / Linux: install Accrue

```bash
cd /path/to/Accrue
chmod +x install/*.sh
bash install/install.sh
bash install/start.sh
```

Stop:

```bash
bash install/stop.sh
```

If `python3 -m venv` fails on Ubuntu, install `python3-venv`.

---

## 6. What to put in `.env` on the new machine

File location: **project root** `.env` (same folder as `README.md`).

The installer copies `.env.example`. For a demo on a new laptop, the defaults are enough. Change these if you share the machine:

```env
APP_SECRET_KEY=pick-a-long-random-string-for-this-pc
DEMO_CSM_PASSWORD=AccrueDemo!2026
DEMO_ADMIN_PASSWORD=AccrueAdmin!2026
```

SQLite (default — no extra install):

```env
DATABASE_URL=sqlite:///./backend/data/accrue.db
```

The app resolves that file to:

```
<project-root>/backend/data/accrue.db
```

CORS (keep these if you use the Vite UI):

```env
APP_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080
```

Memory / LLM stay on **mock** until you have keys:

```env
HINDSIGHT_MODE=mock
LLM_MODE=mock
```

Optional live Groq:

```env
LLM_MODE=groq
GROQ_API_KEY=gsk_...
```

Never commit `.env` with real keys.

---

## 7. Paths the app uses (no extra PATH needed after install)

After install, start scripts call tools by **full path**, so you do not need `.venv` on the system PATH.

| Item | Typical Windows path |
|---|---|
| Project root | `C:\Accrue` (wherever you extracted) |
| Installer | `C:\Accrue\install\install.bat` |
| Python venv | `C:\Accrue\.venv\Scripts\python.exe` |
| pip | `C:\Accrue\.venv\Scripts\pip.exe` |
| Backend code | `C:\Accrue\backend\app` |
| `PYTHONPATH` (set by start script) | `C:\Accrue\backend` |
| SQLite DB | `C:\Accrue\backend\data\accrue.db` |
| Frontend | `C:\Accrue\frontend` |
| npm packages | `C:\Accrue\frontend\node_modules` |
| Env file | `C:\Accrue\.env` |
| Install marker | `C:\Accrue\.accrue\install-info.txt` |

macOS/Linux venv Python: `<project>/.venv/bin/python`

### Manual start (if you do not use start.bat)

**Terminal 1 — API**

```powershell
cd C:\Accrue
.\.venv\Scripts\Activate.ps1
cd backend
$env:PYTHONPATH = "C:\Accrue\backend"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

**Terminal 2 — UI**

```powershell
cd C:\Accrue\frontend
npm run dev
```

The UI binds to **0.0.0.0:5173** (IPv4 and IPv6). Open **http://127.0.0.1:5173** (not only `localhost` if IPv6 is odd on that PC).

---

## 8. First-run checklist

1. `install\install.bat` finished without FAIL
2. `install\start.bat` opened two windows
3. Browser: http://127.0.0.1:5173 shows the Accrue login
4. Sign in as CSM
5. Account **Acme Cloud** is listed
6. **Run 60s demo** fills Priya’s mail and a brief
7. **Ask this company**: “What is Priya telling in this mail?” quotes the live email

If login fails with “backend on port 8000”, the API window crashed or port 8000 is taken. Check the API terminal for the traceback.

---

## 9. Docker (optional, any OS with Docker Desktop)

From the project root:

```powershell
docker compose up --build
```

- UI: http://localhost:8080  
- API: http://localhost:8000  

Uses PostgreSQL instead of SQLite. Stop with `docker compose down`.

---

## 10. Firewall and antivirus

- Windows may ask to allow Node / Python on private networks. Allow **private**.
- If the UI loads but login hangs, allow **python.exe** and **node.exe** through the firewall, or use `127.0.0.1` only (no remote access needed).

---

## 11. Uninstall

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File install\uninstall.ps1
```

Type `YES`. This deletes `.venv`, `node_modules`, and the demo SQLite file. Source code stays.

Then optionally delete the whole project folder. Python and Node stay on the PC (they are shared tools).

To remove Python/Node PATH entries: Environment Variables → Path → delete the lines you added.

---

## 12. Troubleshooting

| Symptom | Fix |
|---|---|
| `python` not found | Reinstall Python with Add to PATH; new terminal; disable Store aliases |
| `node` not found | Reinstall Node LTS; add `C:\Program Files\nodejs\` to User PATH |
| `ExecutionPolicy` error | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| Port 5173 in use | `install\stop.bat` or change nothing and close the other Vite app |
| Port 8000 in use | Stop the other API; `install\stop.bat` |
| Blank page on localhost | Use http://127.0.0.1:5173 |
| Empty JSON / login error | Start API **before** or together with UI; keep the API window open |
| `pip` SSL / corporate proxy | Configure pip proxy, or use a phone hotspot once for install |
| bcrypt warning in API log | Harmless `(trapped) error reading bcrypt version` |
| npm EPERM on Windows | Close IDEs locking `node_modules`, delete `frontend\node_modules`, run install again |

---

## 13. Files in `install\`

| File | Purpose |
|---|---|
| `install.bat` / `install.ps1` | Windows install |
| `install.sh` | macOS/Linux install |
| `start.bat` / `start.ps1` | Start API + UI |
| `start.sh` | Start on Unix |
| `stop.bat` / `stop.ps1` / `stop.sh` | Stop ports 8000 and 5173 |
| `uninstall.ps1` | Remove local venv/modules/db |
| `package-for-transfer.ps1` | Build zip for another PC |

---

## 14. Security note for a “new system”

Demo passwords are public. Before any real customer data:

1. Change `APP_SECRET_KEY` and demo passwords in `.env`
2. Keep `HINDSIGHT_MODE=mock` / `LLM_MODE=mock` or use your own keys
3. Do not expose ports 5173/8000 to the internet without HTTPS and real auth

The seeded accounts (Acme, Priya Shah, etc.) are **synthetic**.
