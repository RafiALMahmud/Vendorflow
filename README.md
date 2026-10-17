# VendorFlow AI

VendorFlow AI is a two-developer portfolio project for secure vendor onboarding,
document-field review, and explainable human-led application decisions. The MVP
uses FastAPI, PostgreSQL, React, TypeScript, Vite, and Tailwind CSS.

This repository currently contains the Phase 0 runnable baseline: a typed backend
health endpoint, a frontend screen that calls it, PostgreSQL/Alembic wiring, and
the shared verified-vendor snapshot contract used by later review features.

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

Install PostgreSQL for Windows from `https://www.postgresql.org/download/windows/`
and keep the command-line tools selected. In PowerShell, create the local-only
development role and database (PostgreSQL will ask for the `postgres` password):

```powershell
psql -U postgres -c "CREATE ROLE vendorflow WITH LOGIN PASSWORD 'vendorflow';"
psql -U postgres -c "CREATE DATABASE vendorflow OWNER vendorflow;"
```

If `psql` is not found, open **SQL Shell (psql)** from the Start menu or add your
PostgreSQL `bin` directory (for example, `C:\Program Files\PostgreSQL\17\bin`) to
`PATH`. The password above is only a convenient local default; use a different
secret outside local development and update `DATABASE_URL` accordingly.

Copy `.env.example` to `.env`, then apply the sequential Alembic migrations:

```powershell
Copy-Item .env.example .env
Set-Location backend
..\.venv\Scripts\python.exe -m alembic upgrade head
```

The `0001_bootstrap` revision deliberately creates no tables. Phase 1 will add
the first owned identity/vendor schema as the next revision, preserving a single
migration history for both developers.

For macOS/Linux, create and activate the environment with
`python3 -m venv .venv` and `source .venv/bin/activate`; all remaining Python,
Alembic, and npm commands are the same apart from path separators.

## Shared verified-data contract

`backend/app/contracts/verified_data.py` defines the version 1 typed handoff to
Developer 2. A fictional, test-only example lives at
`backend/tests/fixtures/verified_vendor_snapshot.json`. Only a `confirmed_value`
whose `review_status` is `confirmed` or `corrected` is exposed by the
`verified_value` property; unreviewed OCR text remains untrusted.

Do not commit `.env`, credentials, real business records, or uploaded documents.

## Git workflow

Bootstrap work lives on `feat/bootstrap`. After review, push the branch, open a
pull request into `main`, and merge it before either developer creates dependent
feature branches. Keep later feature work in separately reviewed branches.

