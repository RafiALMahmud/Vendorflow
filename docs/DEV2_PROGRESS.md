> Historical 2026-10-18 milestone record. Superseded by [QA_RESULTS.md](QA_RESULTS.md) and [SETUP_REPORT.md](SETUP_REPORT.md) for the 2026-10-19 complete-MVP release.

# Combined Developer 1 + Developer 2 integration

Integrated Developer 1 commit 04b8cf4 into feat/dev2-risk-review, preserving its
stacked history. Main is unchanged. The prior independent milestone is now wired
into the shared identity, document contract, database and frontend routing.

Implemented and exercised:

- Vendor registration/login/profile/upload/extraction/field confirmation from D1.
- Own draft creation, submit/resubmit and status/correction UI at /applications.
- Deterministic risk assessment of the shared verified snapshot; history and
  submission evidence persist in PostgreSQL with rules version and assessed time.
- Admin dashboard counts, searchable/paginated queue, evidence, findings, human
  decisions, correction notes and audit history at /admin.
- Server-side JWT roles, vendor ownership, row locks, expected review versions,
  one active application/vendor constraint and atomic assessment/state/audit writes.
- Sequential Alembic migration 0006_review on D1 revision 0005, without rewriting
  earlier migrations. GitHub Actions now provides a disposable PostgreSQL 17 service.

Validation on 2026-10-18:

- 172 backend tests passed, including PostgreSQL API lifecycle, authorization,
  duplicate submissions, failed assessments, uniqueness and concurrent reviewers.
- 24 frontend tests passed; workers limited to two to avoid resource timeouts on
  the combined suite. ESLint and TypeScript/Vite build passed.
- Fresh PostgreSQL migration through head, alembic check, review downgrade to
  0005 and upgrade back to 0006 passed. pip check passed.
- Live headless Edge browser: login -> draft -> submit -> admin correction ->
  vendor resubmit -> admin approve. Vendor admin-page access denied. No browser
  runtime errors. Desktop and mobile screenshots inspected.

Local hosting: frontend http://localhost:5173, API http://localhost:8000,
Swagger /docs. The isolated PostgreSQL cluster uses 127.0.0.1:55432; existing
system PostgreSQL on 5432 is untouched. Generated demo account credentials are
in ignored .local/LOCAL_ACCOUNTS.txt. Demo documents are explicitly fictional,
and dashboard figures are real DB aggregates of these saved demo applications.

Remaining limitations: teammate review before main merge; no production deployment;
Tesseract not installed (native digital PDF extraction works, scans report processing
failure); memory-only login means browser refresh signs out. These are separate
from the now-working review integration.
