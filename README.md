# VendorFlow AI

VendorFlow AI is a two-developer portfolio project for secure vendor onboarding,
document-field review, and explainable human-led application decisions. The MVP
uses FastAPI, PostgreSQL, React, TypeScript, Vite, and Tailwind CSS.

The current implementation includes the runnable baseline, vendor-only
authentication, vendor company-profile setup/editing, secure private document
uploads/downloads, local PDF text extraction and optional Tesseract OCR,
protected React routes, and the shared verified-vendor snapshot contract.

Application submission, risk assessment, admin review, and approval are not
present in the currently fetched repository state. The vendor dashboard labels
that integration as pending rather than simulating Developer 2 data.

## Prerequisites

- Python 3.11 or newer
- Node.js 20.19 or newer and npm
- PostgreSQL 15 or newer
- Optional: Tesseract 5 for JPG/PNG and image-only PDF OCR

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
This also works when Python itself is installed on another drive.

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
and keep the command-line tools selected. Inspect its Windows service first:

```powershell
Get-Service *postgres*
```

If it is stopped, open PowerShell **as Administrator** and start the exact name
shown above, for example `Start-Service postgresql-x64-18`. A service permission
error is unrelated to Python's installation drive. If the `postgres` password
is forgotten, reset it using PostgreSQL's local administration/recovery process;
never commit the recovered password.

Create the local-only role and separate development and disposable test
databases (PostgreSQL asks for the `postgres` password):

```powershell
psql -U postgres -c "CREATE ROLE vendorflow WITH LOGIN PASSWORD 'vendorflow';"
psql -U postgres -c "CREATE DATABASE vendorflow OWNER vendorflow;"
psql -U postgres -c "CREATE DATABASE vendorflow_test OWNER vendorflow;"
```

If `psql` is not found, open **SQL Shell (psql)** from the Start menu or add your
PostgreSQL `bin` directory (for example, `C:\Program Files\PostgreSQL\18\bin`) to
`PATH`. The password above is only a convenient local default; use a different
secret outside local development and update `DATABASE_URL` accordingly.

Tests drop and recreate tables in `vendorflow_test`. Keep `TEST_DATABASE_URL`
pointed at that dedicated disposable database, never development or production.

Copy `.env.example` to `.env`, then apply the sequential Alembic migrations:

```powershell
Copy-Item .env.example .env
Set-Location backend
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m alembic current
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

Important environment settings are `DATABASE_URL`, `TEST_DATABASE_URL`,
`CORS_ORIGINS`, `JWT_SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`,
`DOCUMENT_STORAGE_DIR`, `DOCUMENT_MAX_FILE_SIZE_BYTES`, `TESSERACT_CMD`,
`TESSERACT_LANGUAGE`, `TESSERACT_TIMEOUT_SECONDS`,
`EXTRACTION_MAX_PDF_PAGES`, and `VITE_API_BASE_URL`. The committed
`.env.example` contains local defaults. Limit CORS to trusted frontend origins
and use an absolute private storage volume outside local development.

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

Optional Windows OCR verification:

```powershell
tesseract --version
Get-Command tesseract
```

If an installed Tesseract 5 executable is not on `PATH`, set its absolute path
in `.env`, for example
`TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe`, then restart the
backend. Never claim a real OCR result when this command is unavailable.

## Fictional demo and complete vendor journey

Regenerate the committed fictional document pack when needed:

```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m scripts.generate_extraction_quality_fixtures
```

Use `backend/tests/fixtures/quality_documents/alpha-trade-license.pdf` for a
Tesseract-independent demo. Register the vendor through `/register`; there is
deliberately no vendor seed command that puts a password in shell history. The
local-only admin seed command above is ready for Developer 2 integration, but
the current branch has no admin review routes.

The PostgreSQL-backed golden-path test executes the real Developer 1 sequence:
register -> login -> create/edit profile -> upload a fictional trade license ->
extract six fields with PyMuPDF -> inspect raw values -> confirm/correct fields
-> reload persisted values -> build the verified snapshot. It then registers a
second vendor and verifies that listing, metadata, download, extracted-field
read, and extracted-field edit access do not expose the first vendor's document.

```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m pytest tests\test_vendor_journey.py -v
```

## Complete release checks

```powershell
# From backend; requires the dedicated PostgreSQL test database.
..\.venv\Scripts\python.exe -m pytest
..\.venv\Scripts\python.exe -m compileall -q app scripts tests
..\.venv\Scripts\alembic.exe check
..\.venv\Scripts\python.exe -m scripts.evaluate_extraction_quality

# From frontend.
npm test -- --run
npm run lint
npm run build
```

Automated OCR subprocesses are mocked for deterministic CI. Run a separate real
OCR smoke only when `tesseract --version` succeeds.

## Known limitations

- Remote `main` currently contains only the original scaffold; Developer 1 work
  is in stacked review PRs and must be merged in dependency order.
- No fetched branch contains Developer 2 application, risk, workflow, audit, or
  admin modules. The submit -> request correction -> resubmit -> approve journey
  has not been run and the project as a whole is not release-complete.
- The quality corpus contains four clean synthetic documents. It is not evidence
  of real-world or multilingual OCR performance.
- OCR runs inside the upload request. Production scale should use a bounded
  background worker and explicit retry orchestration.
- Local private disk lacks production backup, retention, malware scanning, and
  encryption-at-rest controls. Rate limiting and production session rotation
  are also outside this MVP.

Do not commit `.env`, credentials, real business records, or uploaded documents.

## Git workflow

Keep feature work in separately reviewed branches. Authentication work lives on
`feat/vendor-auth`; vendor profile work lives on `feat/vendor-profile` and must
follow it. Secure ingestion lives on `feat/document-upload`; document extraction
follows on `feat/document-extraction` with migration `0005`. Developer 2 must
branch after these revisions merge so Alembic stays sequential.

The Developer 1 stack then continues with field review, verified snapshot,
vendor UI, quality gate, and release-preparation PRs. Review and merge it in
order; shared documentation and future migrations require teammate review.

