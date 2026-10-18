# Final MVP QA results

Date: **2026-10-19, Asia/Dhaka**. Tested implementation:
**d8b40089029f4decc0c0521ae0a820c2a7fa65ef**. Starting combined base: a15d549.
Documentation-only delivery commits attach these results without changing app code.
Branch: feat/complete-vendorflow-mvp. Main and D1's nine open stacked PRs remain untouched.

**MVP acceptance result: PASS.** Every item in FEATURE_CHECKLIST.md has evidence.
No remaining FAIL/BLOCKED/NOT TESTED MVP gate. Human review/merge and production
operations remain outside the local MVP release decision.

## Executed checks

| Command / environment | Actual result | Evidence |
|---|---|---|
| .venv/Scripts/python -m pytest backend/tests, RUN_REAL_OCR=1 | 182 passed, 0 failures/errors/skips | [parsed JUnit summary](evidence/local-test-summary.json) |
| npm test | 27 passed across 11 files | [local summary](evidence/local-test-summary.json) |
| npm run lint | exit 0 | [fresh reproduction](evidence/fresh-checkout.json) |
| npm run build | exit 0; TypeScript and Vite production output | [fresh reproduction](evidence/fresh-checkout.json) |
| pip check (existing and fresh environments) | exit 0, no broken requirements | SETUP_REPORT.md |
| alembic heads / check | one head 0006_review; no new upgrade operations | [migration report](evidence/migrations.json) |
| empty fresh DB: downgrade base -> upgrade head -> check | all exit 0; no existing development data touched | [migration report](evidence/migrations.json) |
| fresh GitHub clone + documented setup + all local checks | all phases exit 0 | [fresh report](evidence/fresh-checkout.json) |
| npm run test:e2e, Edge, live FastAPI/PostgreSQL/Tesseract | 2 passed, 0 skipped/flaky/unexpected | [browser summary](evidence/local-test-summary.json) |
| GitHub Actions | all 4 jobs PASS, incl. Linux real OCR + Chromium browser | [CI record](evidence/ci-results.json) |
| runtime-generated secret scan of tracked files | PASS, zero matching paths | [scan result](evidence/local-test-summary.json) |

CI implementation run: https://github.com/RafiALMahmud/Vendorflow/actions/runs/39157379283
Mandatory backend unit jobs intentionally omit the opt-in installed-OCR test;
the separate release-browser-ocr job executes real OCR and the browser scenarios.
Local and fresh Windows suites explicitly enabled real OCR and skipped nothing.

## Supplied four-PDF measurement

Fixed deterministic risk reference date: 2026-10-19. Extraction was performed with
actual PyMuPDF and Tesseract 5.5.3; the scan has no PDF text layer.

| Fixture | Actual extraction | Exact fields / expected | Status |
|---|---|---:|---|
| 01_valid_trade_license.pdf | pdf_text | 6/6 | PASS |
| 02_valid_business_registration.pdf | pdf_text | 5/5 | PASS |
| 03_valid_tax_certificate.pdf | pdf_text | 6/6 | PASS |
| 04_scanned_expired_name_mismatch.pdf | tesseract_ocr | 6/6 | PASS |
| Total | 3 digital + 1 real OCR | **23/23** | PASS |

[Expected versus actual values](evidence/ocr-results.json) include every field.
Relative to these provided fields: zero false positives or false negatives.
This is a four-document fictional layout-specific sample, not general OCR accuracy,
proof of company legitimacy, a trained model or a production fraud metric.

## Browser and persisted workflow evidence

1. Positive: UI registration/login, profile create/edit, upload 01/02/03, inspect
   actual extracted values and confirm all fields, draft/submit, readiness 100.
   Admin downloads original, opens approval dialog and cancels via Escape (no
   write), requests correction, vendor observes note and actually corrects a
   field, resubmits, admin approves. Audit actions are exactly draft_created,
   submitted, needs_correction, resubmitted, approved. Vendor sees approved.
2. Negative: separate UI vendor/profile uploads image-only 04 through real OCR.
   Unreviewed raw OCR does not assert expiry/name mismatch. After a correction
   request and explicit field confirmation/resubmission, readiness is 25 with
   exactly missing required business registration, expired verified license and
   confirmed company-name mismatch. It remains resubmitted until human rejection
   with a note and confirmation dialog. Vendor sees rejected and logout works.
3. Cross-vendor IDs for metadata/original/fields and application submission are
   denied; vendor admin API access is 403. Server tests additionally cover forged/
   expired tokens, public role escalation, malformed/oversized/spoofed uploads,
   path traversal, invalid transitions, missing notes, stale/double decisions,
   unique active drafts, failed audit rollback and concurrent reviewers with one winner.
4. Desktop/mobile screenshots were inspected; viewport overflow assertion passes.
   No browser runtime errors occurred. Dashboard values are DB aggregates, never
   fixture fallbacks. Fixtures exist in tests only; demos are real saved API records.

Screenshots: [approved desktop](evidence/screenshots/admin-approved-desktop.png),
[approved mobile](evidence/screenshots/admin-approved-mobile.png),
[negative findings](evidence/screenshots/negative-findings.png).

## Resolved failures and scope

The release kit initially exposed separate-line labels, identifier-prefix truncation,
missing certificate-number extraction, and Windows OCR line endings. These were
fixed generically and regression-tested without hardcoding fixture identities.
Portable OCR initially lacked its language-data path; it now has explicit config.
The first browser harness attempt used an exact text-label locator on a select
whose label includes its options; the role/accessible-name locator fixed the harness.
Final browser results above are a fresh passing run, not a claimed pass from that
failed attempt. A non-fatal httpx TestClient deprecation warning remains.

Production deployment, real-world document authenticity, arbitrary document layouts,
backup/retention/rate-limit certification and broad OCR quality are NOT TESTED and
not part of this MVP acceptance checklist. They are not represented as complete.
Memory-only auth deliberately signs out on browser refresh; expiry/logout is tested.
