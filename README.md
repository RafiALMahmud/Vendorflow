# VendorFlow AI

VendorFlow AI is a local MVP for fictional vendor onboarding, private business-document
uploads, human verification of extracted fields, explainable document-review priority,
and auditable admin decisions. It uses FastAPI, PostgreSQL, SQLAlchemy/Alembic,
React/TypeScript/Vite/Tailwind, PyMuPDF and Tesseract. Scores are deterministic
completeness/consistency rules, not fraud probabilities or autonomous decisions.

Both developers' histories are preserved on `feat/complete-vendorflow-mvp`, based
on combined commit a15d549. Main is unchanged. Read the actual release evidence in
[QA_RESULTS](docs/QA_RESULTS.md), the [feature checklist](docs/FEATURE_CHECKLIST.md),
and [integration/provenance audit](docs/INTEGRATION_AUDIT.md).

## Windows prerequisites

Python 3.11+, Node 20.19+ (22 recommended), npm, Git and PostgreSQL 15+ binaries.
This machine was verified with Python 3.12.6, Node 22.21.0, npm 10.9.4, Git
2.48.1 and PostgreSQL 17.7 at `E:\PostgreSQL\17\bin`.

## Automatic local setup

```powershell
Set-Location E:\Vendorflow\Vendorflow
.\scripts\Setup-Local.ps1 -PostgresBin 'E:\PostgreSQL\17\bin'
.\scripts\Start-Local.ps1 -PostgresBin 'E:\PostgreSQL\17\bin'
```

For a fresh clone, replace the first path with your checkout. If execution policy
blocks local scripts, invoke `powershell -NoProfile -ExecutionPolicy Bypass -File
.\scripts\Setup-Local.ps1 -PostgresBin 'E:\PostgreSQL\17\bin'`; this changes policy
for that process only. No permanent machine policy change is needed.

Setup reuses/creates `.venv`, installs `backend[dev]`, installs the locked frontend
with `npm ci`, initializes a **separate project-owned PostgreSQL cluster on
127.0.0.1:55432**, creates development/test databases, applies existing migrations,
and installs project-local Tesseract using micromamba/conda-forge. It does not
install a system service, change global PATH or modify the PostgreSQL service on
5432. PostgreSQL binaries must already exist; no administrator installer is run.
Tesseract's local environment is approximately 217 MB. Use `-SkipOcr` only when
reusing your own configured Tesseract or intentionally accepting blocked scan OCR.

Credentials and JWT secret are generated only for new/default local configuration;
existing non-default `.env` secrets are preserved. `.env`, uploads, local account
files, PostgreSQL data and binaries remain ignored. Test data is fictional.
`vendorflow_test` is disposable: tests drop/recreate its tables. Never point it at
business data. The setup never drops an existing database.

Open [the app](http://localhost:5173), [login](http://localhost:5173/login),
[Swagger](http://localhost:8000/docs), or [health](http://localhost:8000/api/v1/health).
Start/stop scripts manage only recorded server processes:

```powershell
.\scripts\Stop-Local.ps1
```

This leaves PostgreSQL and persisted data running. Logs/process IDs are in ignored
`.local/`. For foreground development, use separate terminals:

```powershell
# Backend, from root:
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload
# Frontend, from root in another terminal:
npm --prefix frontend run dev
```

## Vendor and administrator demo

Register a vendor through `/register`, log in, create/edit a profile, upload the
three positive fixtures, and confirm extracted fields under Documents. Use
`/applications` to create a draft, submit, see correction notes and resubmit.

Create an admin through the existing local-only management command (never public
registration). It prompts for the password without putting it in shell history:

```powershell
.\.venv\Scripts\python.exe -m app.scripts.seed_admin --email reviewer@example.com --full-name 'Local Reviewer'
```

Sign in at `/login`; admin users land at `/admin`. Dashboard counts come from
PostgreSQL. Open a submitted case to inspect immutable submission evidence,
download original documents, view findings, and confirm a human decision.
Rejection/correction requires a note. A stale case returns 409 and must be reloaded.

Previously created local demo credentials remain in `.local/LOCAL_ACCOUNTS.txt`
on this workstation only; that file is not included in a clone. Authentication
is memory-only by design: refresh signs out; logout/expiry clears the user and
expired authenticated requests redirect back to login. No browser token store or
parallel authentication system was added.

## Four supplied QA documents and OCR

The fictional fixtures and ground truth live in
`backend/tests/fixtures/vendorflow_qa/`. They have no legal validity.

| Files | Objective |
|---|---|
| 01 trade license, 02 business registration, 03 tax certificate | NORTHSTAR positive workflow |
| 04 image-only trade license | EASTBRIDGE expired/name-mismatch after human confirmation |

The parser supports the documented label:value, label-on-next-line and OCR-column
formats, including certificate number. It does not claim arbitrary document-layout
coverage. Digital PDFs use text first; scans/images use actual Tesseract.
Set `TESSERACT_CMD` and optionally `TESSERACT_DATA_DIR` in ignored `.env` for a custom
installation. `TESSERACT_LANGUAGE=eng` is the fixture language. Missing OCR produces
a visible failed state; Retry extraction can retry a failed file without replacing
it. Successful/verified documents cannot be reprocessed through that endpoint.

The measured four-file result is in [OCR evidence](docs/evidence/ocr-results.json).
That small synthetic denominator is not general OCR accuracy.

## Tests and production build

```powershell
Set-Location E:\Vendorflow\Vendorflow
.\.venv\Scripts\python.exe -m pip check
$env:RUN_REAL_OCR = '1'
.\.venv\Scripts\python.exe -m pytest backend/tests
# Without real OCR, omit RUN_REAL_OCR; only the explicit real-OCR test skips.
Set-Location frontend
npm test
npm run lint
npm run build
# Browser QA uses generated fictional users in the configured local development DB.
$env:PLAYWRIGHT_CHANNEL = 'msedge'
npm run test:e2e
```

For bundled Chromium instead of installed Edge: `npx playwright install chromium`,
remove PLAYWRIGHT_CHANNEL, then run `npm run test:e2e`. Tests launch servers if not
already running. Credentials are generated in ignored `.local/browser-qa.json`;
no passwords or JWT traces are published. Browser reports/screenshots are under
`.local/browser-results.json` and `frontend/test-results/`.

```powershell
# From backend:
..\.venv\Scripts\python.exe -m alembic heads
..\.venv\Scripts\python.exe -m alembic check
..\.venv\Scripts\python.exe -m scripts.evaluate_release_fixtures --output ../.local/ocr-results.json
```

CI runs the backend on Python 3.11/3.12, frontend tests/lint/build, and a separate
real Tesseract + Chromium/PostgreSQL browser acceptance job. No paid service,
AWS credentials or local Docker is needed. Database rollback checks run on the
isolated CI/test database, never a development database with user records.

## Troubleshooting and limits

- Windows EPERM during npm ci: stop the recorded Vite server with Stop-Local.ps1,
  then rerun setup. Do not delete another developer's files or kill all Node processes.
- Port in use: start refuses to overwrite another service. Stop the intended local
  server or deliberately change its port and matching CORS/API settings.
- PostgreSQL password: the project cluster has generated local credentials; it
  does not need or reset the existing system PostgreSQL admin password.
- OCR language errors: verify TESSERACT_DATA_DIR contains eng.traineddata and
  restart the backend. The supplied portable installation uses .local/ocr/share/tessdata.
- The access token is intentionally not persistent across a full browser refresh.
- The MVP uses local private disk and synchronous extraction workers. Production
  deployment still needs operational rate limits, backups/retention, transport TLS,
  robust job orchestration and session rotation. This release is a local MVP,
  not a security certification or a claim of real-world vendor legitimacy.

Read [architecture](docs/ARCHITECTURE.md), [API](docs/API.md),
[database](docs/DATABASE.md), [rules](docs/RISK_RULES.md),
[workflows](docs/WORKFLOWS.md), [demo](docs/DEMO.md) and
[contributions](docs/CONTRIBUTIONS.md). Open a review PR; do not push or merge main
without team review. Existing D1 stacked PRs are documented in the integration audit.
