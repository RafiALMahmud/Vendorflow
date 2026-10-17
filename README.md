# VendorFlow AI

VendorFlow AI is a two-developer portfolio project for secure vendor onboarding,
document-field review, and explainable human-led application decisions. The MVP
uses FastAPI, PostgreSQL, React, TypeScript, Vite, and Tailwind CSS.

This repository currently contains the Phase 0 runnable baseline: a typed backend
health endpoint and a frontend screen that calls it. Product scope and ownership
are defined in `PROJECT_SPEC.md` and `TEAM_TASKS.md`.

## Prerequisites

- Python 3.11 or newer
- Node.js 20.19 or newer and npm
- PostgreSQL 15 or newer (needed when database-backed features begin)

The health endpoint does not query PostgreSQL, so the Phase 0 smoke test works
before a local database is created.

## First-time setup (Windows PowerShell)

From the repository root:

```powershell
Copy-Item .env.example .env
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".\backend[dev]"

Set-Location frontend
npm install
Set-Location ..
```

If PowerShell blocks virtual-environment activation, run commands directly with
`.\.venv\Scripts\python.exe` instead of changing your machine's execution policy.

## Run locally

Open two PowerShell terminals at the repository root.

Backend:

```powershell
.\.venv\Scripts\Activate.ps1
Set-Location backend
uvicorn app.main:app --reload
```

Frontend:

```powershell
Set-Location frontend
npm run dev
```

Open `http://localhost:5173`. The page should report **Backend online**. API docs
are available at `http://localhost:8000/docs`, and the health endpoint is
`GET http://localhost:8000/api/v1/health`.

## Tests and checks

```powershell
# From the repository root
.\.venv\Scripts\python.exe -m pytest backend\tests

Set-Location frontend
npm test
npm run lint
npm run build
```

## Database and migrations

Copy `.env.example` to `.env` and change `DATABASE_URL` for your local PostgreSQL
credentials. Alembic is configured now; the first schema migration will be added
with the identity and vendor models in Phase 1.

```powershell
Set-Location backend
alembic upgrade head
```

Do not commit `.env`, credentials, real business records, or uploaded documents.

## Git workflow

Bootstrap work lives on `feat/bootstrap`. After review, push the branch, open a
pull request into `main`, and merge it before either developer creates dependent
feature branches. See `TEAM_TASKS.md` for ownership and merge order.

