# Integrated local environment

Checkout: E:\Vendorflow\Vendorflow, branch feat/dev2-risk-review.
Python 3.12.6, Node 22.21.0, npm 10.9.4, Git 2.48.1, PostgreSQL 17.7.
Both developers' backend dependencies installed into .venv and frontend dependencies
installed with npm ci from the merged lockfile. No system package versions changed.

The existing PostgreSQL service on 5432 required unknown credentials. Instead of
changing its authentication or databases, initialized a separate user-owned cluster
with the installed E:\PostgreSQL\17\bin tools. Its ignored data/config files live
in .local/postgres and .local/postgres-config.json. It listens on 127.0.0.1:55432
with SCRAM password authentication, a separate cluster-admin role, an app role,
and separate vendorflow and disposable vendorflow_test databases. Generated
credentials and JWT secret are in ignored .env; no secrets are committed.

The default example DB URLs were replaced only after checking they were placeholder
values. Document uploads are isolated under .local/private_uploads. Test fixtures
only drop/recreate vendorflow_test tables. Do not use a database containing real data
for TEST_DATABASE_URL. Existing non-default secrets/configuration were preserved.

Applied existing revisions 0001-0005, then generated/reviewed/applied sequential
0006_review. Tested zero-to-head, review downgrade/upgrade, and alembic check.

Run checks:

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests
.\.venv\Scripts\python.exe -m pip check
# In frontend:
npm test
npm run lint
npm run build
```

Run servers using the README commands. For this session, hidden background processes
serve frontend 5173 and backend 8000. Process IDs and logs are in
$env:TEMP/vendorflow-local/processes.json. The isolated database remains running.
After a reboot start it with the installed pg_ctl, -D pointing at the absolute
.local/postgres path, -l pointing at a local log file, and
-o "-h 127.0.0.1 -p 55432". Do not start a second instance against the same data directory.

Local fictional vendor/admin accounts were created only in this new development
database. Read .local/LOCAL_ACCOUNTS.txt for generated credentials. Sign in via
/login; admins land at /admin and vendors at /dashboard. AuthProvider deliberately
keeps JWTs in memory, so a full browser refresh requires signing in again.

Tesseract is not installed. Digital PDFs use real PyMuPDF extraction; image OCR
reports its processing failure explicitly. Test OCR is mocked. The dependency stack
emits a non-fatal httpx TestClient deprecation warning; checks pass.
