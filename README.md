# VendorFlow AI

VendorFlow AI is a two-developer portfolio project for secure vendor onboarding,
document-field review, and explainable human-led application decisions. The MVP
uses FastAPI, PostgreSQL, React, TypeScript, Vite, and Tailwind CSS.

The current implementation includes the runnable baseline, vendor-only
authentication, vendor company-profile setup/editing, secure private document
uploads/downloads, local PDF text extraction and optional Tesseract OCR,
protected React routes, and the shared verified-vendor snapshot contract.

## Prerequisites

- Python 3.11 or newer
- Node.js 20.19 or newer and npm
- PostgreSQL 15 or newer (needed when database-backed features begin)

The health endpoint does not query PostgreSQL, but authentication and its tests
require the development and isolated test databases described below.

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
psql -U postgres -c "CREATE DATABASE vendorflow_test OWNER vendorflow;"
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

`0001_bootstrap` establishes the migration history, `0002_create_users` creates
the identity table, `0003_create_vendors` creates the one-to-one company profile
table, `0004_create_documents` creates document and extracted-field tables, and
`0005_add_extraction_state` adds safe failure and normalization details.
Developer 2 must add later migrations sequentially after these Developer 1
migrations are merged; do not create a parallel migration head.

Generate a new JWT secret for `.env` instead of using the development fallback:

```powershell
[Convert]::ToHexString(
  [Security.Cryptography.RandomNumberGenerator]::GetBytes(32)
).ToLower()
```

Set that output as `JWT_SECRET_KEY`. Access tokens expire after
`ACCESS_TOKEN_EXPIRE_MINUTES` (30 by default).

For macOS/Linux, create and activate the environment with
`python3 -m venv .venv` and `source .venv/bin/activate`; all remaining Python,
Alembic, and npm commands are the same apart from path separators.

## Shared verified-data contract

`backend/app/contracts/verified_data.py` defines the version 1 typed handoff to
Developer 2. A fictional, test-only example lives at
`backend/tests/fixtures/verified_vendor_snapshot.json`. Only a `confirmed_value`
whose `review_status` is `confirmed` or `corrected` is exposed by the
`verified_value` property; unreviewed OCR text remains untrusted.

## Authentication

Public registration accepts only `email`, `full_name`, and `password`; unknown
fields such as `role` are rejected. Every public account is assigned the
`vendor` role on the server. API examples are in `docs/API_CONTRACTS.md`.

The browser keeps the short-lived access token only in React memory. It is not
written to `localStorage`, `sessionStorage`, URLs, or logs, reducing persistence
if injected JavaScript runs. This MVP therefore signs the user out on a full page
refresh. A future production session design should use a Secure, HttpOnly,
SameSite cookie with CSRF protection and token rotation.

Create a local admin only after migrations have run. The command is disabled
outside `development`/`test` and prompts securely so the password is not placed
in shell history or process arguments:

```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m app.scripts.seed_admin `
  --email admin@example.com `
  --full-name "Local Review Admin"
```

There is intentionally no public admin-registration endpoint.

## Vendor profile

After signing in as a vendor, open `http://localhost:5173/profile`. A new account
sees the setup form; an account with a profile sees the saved values and may edit
them. The page calls the real `POST`, `GET`, and `PATCH /api/v1/vendors/me`
endpoints and shows loading, success, validation, and API error states.

The backend derives ownership only from the signed-in user. Clients cannot
provide or change `owner_user_id`, and the database enforces one profile per
user. Exact request and response examples are in `docs/API_CONTRACTS.md`.

## Secure document uploads

After creating a vendor profile, open `http://localhost:5173/documents` to upload
or list the authenticated vendor's documents. Uploads use multipart form fields
named `document_type` and `file`. New records start as `uploaded`, transition
through `processing`, and finish as `processed` or `failed`.

Configuration in `.env`:

```text
DOCUMENT_STORAGE_DIR=private_uploads
DOCUMENT_MAX_FILE_SIZE_BYTES=10485760
```

Relative storage paths resolve from the repository root. Use an absolute path
for a deployment volume. The storage directory is ignored by Git and is never
mounted as a public/static directory. The backend streams uploads with the byte
limit, checks the filename, declared type, magic bytes, and real PDF/image
structure, then stores the file under a generated UUID name. Supported files are
PDF, JPG/JPEG, and PNG only.

If metadata persistence fails, the newly stored file is removed. File downloads
first query the document through the authenticated vendor's profile and return
`404` for another vendor's document. Exact requests and responses are in
`docs/API_CONTRACTS.md`.

Digital PDFs use PyMuPDF selectable text without OCR. Image-only PDFs and image
uploads use a locally installed Tesseract executable. Missing Tesseract is
reported honestly as a failed OCR-required document; it does not prevent digital
PDF processing. Installation, parsing, date ambiguity, and test instructions are
in `docs/DOCUMENT_EXTRACTION.md`.

Do not commit `.env`, credentials, real business records, or uploaded documents.

## Git workflow

Keep feature work in separately reviewed branches. Authentication work lives on
`feat/vendor-auth`; vendor profile work lives on `feat/vendor-profile` and must
follow it. Secure ingestion lives on `feat/document-upload`; document extraction
follows on `feat/document-extraction` with migration `0005`. Developer 2 must
branch after these revisions merge so Alembic stays sequential.

