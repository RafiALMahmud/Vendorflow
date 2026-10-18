# Developer 2 local environment — 2026-10-18

Checkout: `E:\Vendorflow\Vendorflow`, cloned without replacing the supplied
planning files in its parent. Starting main: `aa591b8`. Ran `git fetch origin`,
`git switch main`, `git pull --ff-only origin main`, and created
`feat/dev2-risk-review`. No existing developer changes were present or overwritten.
Read the complete supplied CODEX_DEV2_START.md, PROJECT_SPEC.md and TEAM_TASKS.md;
the latter two were copied locally into the clone and remain ignored as configured.

| Prerequisite | Actual version/status |
| --- | --- |
| Python | 3.12.6 |
| Node | 22.21.0 |
| npm | 10.9.4 |
| Git | 2.48.1.windows.1 |
| PostgreSQL | 17.7, existing postgresql-x64-17 service running, port 5432 accepting |

PostgreSQL binaries are at `E:\PostgreSQL\17\bin` and absent from PATH; no global
PATH change or installation was necessary. Configured `.env.example` database
credentials did not establish a connection. No roles/databases/passwords were
modified. Configure an isolated project DB URL in ignored `.env` using a valid
local PostgreSQL login; do not send or commit that password. Base migrations must
also merge before review persistence. `alembic heads` and `alembic history` run
successfully from `backend` and return no revisions. Upgrade was not run against
an unverified DB; no speculative migration was created.

Executed dependency setup from checkout root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e './backend[dev]'
Set-Location frontend
npm ci
```

Key installed backend packages: pip 26.2.1, FastAPI 0.143.5, Pydantic 2.14.1,
pydantic-settings 2.16.0, SQLAlchemy 2.1.5, psycopg 3.3.6, Alembic 1.20.0,
uvicorn 0.54.0, pytest 8.4.2, httpx 0.28.1. `pip check` reports no broken requirements.
Frontend: React 19.3.1, TypeScript 5.8.3, Vite 6.4.4, Vitest 5.0.5,
Tailwind 4.3.3, ESLint 9.39.5. Used the committed npm lockfile without changes;
npm reported 0 vulnerabilities. No project dependency versions were changed.

Created root `.env` from example and `frontend/.env` only if absent. Both are
ignored. No credentials were printed or committed. Baseline frontend test,
lint and build passed. Initial backend health-test collection failed due to the
example's comma-separated CORS setting; a minimal `NoDecode` annotation and
JSON/CSV parser fix in shared `core/config.py` resolves it. This shared change
requires Dev 1 review; existing auth/vendor/UI entrypoints were not modified.

Validation commands (from checkout root unless noted):

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests --cov=app.services --cov-report=term-missing
.\.venv\Scripts\python.exe -m pip check
# In frontend:
npm test
npm run lint
npm run build
# Back at root, after build:
.\.venv\Scripts\python.exe scripts/dev2_smoke.py
```

Smoke checks start disposable servers, verify actual health/CORS and Vite
production HTML/JS/CSS responses, and stop them in a finally block. They do not
exercise browser rendering or authenticate against nonexistent review endpoints.
The existing FastAPI TestClient stack emits an httpx deprecation warning; tests
pass. Dependency churn solely to remove that warning was avoided.
