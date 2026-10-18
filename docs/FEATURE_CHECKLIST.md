# Full MVP feature checklist

Implementation under test: `d8b40089029f4decc0c0521ae0a820c2a7fa65ef`. Date: 2026-10-19, Asia/Dhaka.
All 38 items from the supplied FULL_QA_CHECKLIST.md have PASS evidence. No FAIL, BLOCKED or NOT TESTED items remain in this MVP checklist. Team review and main merge remain human actions, as requested.

The profile checklist wording "CRUD" means the agreed create/read/update `/vendors/me` contract; no profile deletion endpoint was specified. Audit integrity covers application review actions and immutable submission snapshots. This is not a production security certification.

| Done | Acceptance item | Status | Evidence | Tested SHA / date |
|---|---|---|---|---|
| [x] | Current remote branch graph and nine stacked PRs audited; integration base documented. | PASS | [Integration audit](INTEGRATION_AUDIT.md); [PR description](PR_DESCRIPTION.md) | `d8b4008` / 2026-10-19 |
| [x] | No uncommitted work lost, no collaborator branches force-pushed, no accidental duplicate cherry-picks. | PASS | [Integration audit](INTEGRATION_AUDIT.md); [PR description](PR_DESCRIPTION.md) | `d8b4008` / 2026-10-19 |
| [x] | Integration work on a new branch; PR prepared for team review; main untouched. | PASS | [Integration audit](INTEGRATION_AUDIT.md); [PR description](PR_DESCRIPTION.md) | `d8b4008` / 2026-10-19 |
| [x] | Authorship/provenance documented. | PASS | [Integration audit](INTEGRATION_AUDIT.md); [PR description](PR_DESCRIPTION.md) | `d8b4008` / 2026-10-19 |
| [x] | Python/Node/npm/Git/PostgreSQL versions validated, install succeeds from fresh checkout. | PASS | [Fresh checkout](evidence/fresh-checkout.json); [setup](SETUP_REPORT.md) | `d8b4008` / 2026-10-19 |
| [x] | Isolated development and test DB configured safely; `.env` gitignored. | PASS | [Setup](SETUP_REPORT.md); [secret scan](evidence/local-test-summary.json) | `d8b4008` / 2026-10-19 |
| [x] | SQLAlchemy models use the same registry, proper FKs/constraints/indexes. | PASS | [Integration audit](INTEGRATION_AUDIT.md); [PR description](PR_DESCRIPTION.md) | `d8b4008` / 2026-10-19 |
| [x] | `alembic heads` yields one head; fresh migrations pass. | PASS | [Fresh checkout](evidence/fresh-checkout.json); [setup](SETUP_REPORT.md) | `d8b4008` / 2026-10-19 |
| [x] | App starts: FastAPI health/API docs and React UI respond. | PASS | [Live browser cases](../frontend/e2e/onboarding.spec.ts); [browser results](evidence/local-test-summary.json) | `d8b4008` / 2026-10-19 |
| [x] | Vendor registration/login/logout/session-expiry behavior works; public registration cannot make admins. | PASS | [Auth/profile tests](../backend/tests/test_auth.py); [profile tests](../backend/tests/test_vendors.py); [expiry tests](../frontend/src/features/auth/SessionExpiry.test.tsx) | `d8b4008` / 2026-10-19 |
| [x] | Protected vendor profile CRUD works. | PASS | [Integration audit](INTEGRATION_AUDIT.md); [PR description](PR_DESCRIPTION.md) | `d8b4008` / 2026-10-19 |
| [x] | Upload accepts valid PDF/JPG/PNG, rejects unsafe/malformed/oversized files. | PASS | [Upload security](../backend/tests/test_documents.py); [evidence/retry](../backend/tests/test_release_api.py) | `d8b4008` / 2026-10-19 |
| [x] | Documents stored outside public static paths, downloadable only by owner/authorized admin. | PASS | [Upload security](../backend/tests/test_documents.py); [evidence/retry](../backend/tests/test_release_api.py) | `d8b4008` / 2026-10-19 |
| [x] | Text PDF extraction matches fictional test fixture ground truth. | PASS | [23/23 extraction](evidence/ocr-results.json); [real OCR regression](../backend/tests/test_release_acceptance.py) | `d8b4008` / 2026-10-19 |
| [x] | Scanned OCR works with real Tesseract on image-only PDF, or explicitly BLOCKED. | PASS | [23/23 extraction](evidence/ocr-results.json); [real OCR regression](../backend/tests/test_release_acceptance.py) | `d8b4008` / 2026-10-19 |
| [x] | Extracted raw/confirmed fields saved, edited and confirmed by the correct vendor. | PASS | [Field review](../backend/tests/test_extracted_field_review.py); [browser confirmation](../frontend/e2e/onboarding.spec.ts) | `d8b4008` / 2026-10-19 |
| [x] | Vendor document UI shows live status, errors, retry and real extracted fields. | PASS | [Field review](../backend/tests/test_extracted_field_review.py); [browser confirmation](../frontend/e2e/onboarding.spec.ts) | `d8b4008` / 2026-10-19 |
| [x] | Application draft/create/status/submit/resubmit APIs work with authorization. | PASS | [API lifecycle](../backend/tests/test_admin.py); [real browser lifecycle](../frontend/e2e/onboarding.spec.ts); [results](QA_RESULTS.md) | `d8b4008` / 2026-10-19 |
| [x] | Risk engine uses verified snapshot; scores bounded and findings explained. | PASS | [Risk rules](../backend/tests/test_risk_engine.py); [release fixtures](../backend/tests/test_release_acceptance.py) | `d8b4008` / 2026-10-19 |
| [x] | Missing/expired/mismatch/unconfirmed flags and no double counting tested. | PASS | [Risk rules](../backend/tests/test_risk_engine.py); [release fixtures](../backend/tests/test_release_acceptance.py) | `d8b4008` / 2026-10-19 |
| [x] | State machine permits only specified transitions and returns 409 for invalid transitions. | PASS | [PostgreSQL admin tests](../backend/tests/test_admin.py); [all state pairs](../backend/tests/test_workflow.py) | `d8b4008` / 2026-10-19 |
| [x] | Review notes required for reject/request correction. | PASS | [PostgreSQL admin tests](../backend/tests/test_admin.py); [all state pairs](../backend/tests/test_workflow.py) | `d8b4008` / 2026-10-19 |
| [x] | Admin decisions and audit records committed atomically; repeated/concurrent actions safe. | PASS | [PostgreSQL admin tests](../backend/tests/test_admin.py); [all state pairs](../backend/tests/test_workflow.py) | `d8b4008` / 2026-10-19 |
| [x] | Role-protected admin dashboard, list/filter/paginate, details and risk findings show REAL API data. | PASS | [Integration audit](INTEGRATION_AUDIT.md); [PR description](PR_DESCRIPTION.md) | `d8b4008` / 2026-10-19 |
| [x] | Approve/reject/request correction buttons work; errors/loading/empty states handled. | PASS | [Integration audit](INTEGRATION_AUDIT.md); [PR description](PR_DESCRIPTION.md) | `d8b4008` / 2026-10-19 |
| [x] | Vendor sees correction request and can resubmit with new assessment. | PASS | [API lifecycle](../backend/tests/test_admin.py); [real browser lifecycle](../frontend/e2e/onboarding.spec.ts); [results](QA_RESULTS.md) | `d8b4008` / 2026-10-19 |
| [x] | Positive: fictional NORTHSTAR profile + PDFs 01,02,03 -> verified fields -> submitted -> correction -> resubmitted -> approved -> persistent audit. | PASS | [Integration audit](INTEGRATION_AUDIT.md); [PR description](PR_DESCRIPTION.md) | `d8b4008` / 2026-10-19 |
| [x] | Negative: separate vendor + scanned PDF 04 -> expired/mismatch warnings after verification, no automatic rejection. | PASS | [Real browser cases](../frontend/e2e/onboarding.spec.ts); [passing CI](evidence/ci-results.json) | `d8b4008` / 2026-10-19 |
| [x] | Vendor A denied access to Vendor B profile, documents, files, extracted fields and applications. | PASS | [Integration audit](INTEGRATION_AUDIT.md); [PR description](PR_DESCRIPTION.md) | `d8b4008` / 2026-10-19 |
| [x] | Vendor cannot access admin APIs or tamper with role/score/status fields. | PASS | [API security](../backend/tests/test_admin.py); [cross-vendor browser checks](../frontend/e2e/onboarding.spec.ts) | `d8b4008` / 2026-10-19 |
| [x] | Admin dashboard counts match persisted records after workflow changes. | PASS | [API lifecycle](../backend/tests/test_admin.py); [real browser lifecycle](../frontend/e2e/onboarding.spec.ts); [results](QA_RESULTS.md) | `d8b4008` / 2026-10-19 |
| [x] | Backend pytest suite passes; DB API integration and edge cases included. | PASS | [182 tests incl. real OCR](evidence/local-test-summary.json); [fresh suite](evidence/fresh-checkout.json) | `d8b4008` / 2026-10-19 |
| [x] | Frontend tests pass, TypeScript production build and lint pass. | PASS | [Integration audit](INTEGRATION_AUDIT.md); [PR description](PR_DESCRIPTION.md) | `d8b4008` / 2026-10-19 |
| [x] | CI passes or external access limitation documented. | PASS | [All four CI jobs](evidence/ci-results.json) | `d8b4008` / 2026-10-19 |
| [x] | No secrets, uploaded personal docs, unsafe files or real IDs are committed. | PASS | [Setup](SETUP_REPORT.md); [secret scan](evidence/local-test-summary.json) | `d8b4008` / 2026-10-19 |
| [x] | Measured OCR accuracy reported with exact denominator and dependency availability; no invented claims. | PASS | [23/23 extraction](evidence/ocr-results.json); [real OCR regression](../backend/tests/test_release_acceptance.py) | `d8b4008` / 2026-10-19 |
| [x] | README, architecture, API, demo, contributors, setup, QA evidence and troubleshooting updated. | PASS | [README](../README.md); [architecture](ARCHITECTURE.md); [demo](DEMO.md); [API](API.md) | `d8b4008` / 2026-10-19 |
| [x] | Fresh-checkout reproducibility verified on documented environment. | PASS | [Fresh checkout](evidence/fresh-checkout.json); [setup](SETUP_REPORT.md) | `d8b4008` / 2026-10-19 |
