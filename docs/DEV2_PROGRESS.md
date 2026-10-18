# Developer 2 progress

This is an independently tested milestone on `feat/dev2-risk-review`, not a
completed PostgreSQL-backed review product.

Implemented:

- D2-03: typed, configurable pure risk engine with stable codes, evidence,
  deterministic ordering, verified-value semantics, score clamping and date checks.
- D2-06 policy portion: legal transitions, owning-vendor/admin policy, required
  decision reasons, bounded notes, UTC audit-event plan and strict review payload.
- D2-05 UI portion: typed admin counts/queue, filtering/search/paging, evidence,
  findings, human review controls, stale-decision protection and audit feed.
- D2-02 UI portion: status/correction/submit/resubmit widget with pending/errors.
- D2-08: GitHub Actions runs backend tests on Python 3.11/3.12 and frontend
  tests/lint/build on Node 22. It requires neither DB, AWS nor OCR for this milestone.
- Project configuration repair, reproducible live baseline smoke script, risk,
  workflow, API and setup/handoff documentation.

Feature UI uses injected APIs/callbacks and is exercised with fixtures exclusively
in tests. It is intentionally not mounted into the shared health app until the
authenticated transport and routes exist. There are no production fixture metrics.

Validation: backend 82 tests passed, frontend 9 tests passed, ESLint passed,
TypeScript/Vite production build passed, pip dependency check passed, live backend
health/CORS and frontend production assets passed. Backend risk/workflow service
statement coverage is 100%. GitHub-hosted CI results are not yet verified.

Blocked integration and next sequence:

1. Dev 1 merges User/Vendor/auth, shared snapshot contract/builder, authenticated
   frontend client/context and base Alembic revisions.
2. Rebase/merge updated main on this feature branch without rewriting others' work;
   import the actual shared schema and identity dependencies.
3. Add Application/RiskAssessment/AuditEvent on existing ORM Base and sequential
   PostgreSQL migration; implement secure API queries and atomic assessment/audit
   persistence with row locking/version checks and active-application uniqueness.
4. Run PostgreSQL migration/rollback/concurrency and FastAPI authorization tests;
   mount the UI through owner-reviewed shared entrypoint changes.
5. Run vendor submit -> correction -> resubmit -> admin approve through actual
   APIs/browser. Only then mark the full vertical slice complete.

Local database setup additionally needs a working PostgreSQL login in ignored
`.env`. No database or authentication settings were altered to bypass this.
See REVIEW_WORKFLOW.md and API_CONTRACTS.md for the concrete integration proposal.
