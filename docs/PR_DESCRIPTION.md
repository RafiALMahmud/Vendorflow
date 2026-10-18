# Complete VendorFlow AI MVP and verify the supplied release kit

The prior combined branch already contained D1 identity/document/vendor work and
D2 persisted risk/review workflows. The supplied PDFs exposed unsupported field
layouts and the scanned scenario had no installed OCR verification. This branch
preserves both histories and finishes the release gaps on top of a15d549.

- Parse the supplied label/value layouts without truncating REG/TIN identifiers;
  support certificate numbers and Windows OCR line endings.
- Configure project-local OCR/PostgreSQL without admin/system changes; add safe
  setup/start/stop scripts and preserve existing secrets/data.
- Add session expiry, failed-extraction retry, authorized original-evidence download,
  accessible review confirmation/cancellation and regression coverage.
- Add real browser acceptance, a separate Linux Tesseract/Chromium CI job,
  fictional fixture measurement, fresh-checkout validation and full release docs.

Validation: 182 backend tests (real OCR enabled), 27 frontend tests, lint/build,
full empty-DB migration round trip, fresh GitHub checkout/setup, and two real
browser scenarios passed. All four implementation CI jobs passed. The four supplied
fictional PDFs matched 23/23 expected fields; this is not general OCR accuracy.

Schema: no new migration needed; existing linear head 0006_review is preserved.
Security: original files are available only to the owner or admin in saved case
evidence; reviewed fields cannot be overwritten by retry; existing JWT/ownership
and transaction/concurrency rules remain authoritative. No production auth,
identity, OCR or risk service was replaced. No runtime secrets/uploads are committed.

Authorship: D1 original modules and D2 original modules remain attributed in
CONTRIBUTIONS.md and INTEGRATION_AUDIT.md. D1 PRs #1-#9 remain open and untouched;
the combined base already contains all their ancestors. Do not merge the stacked
PRs again on top of this branch. Coordinate team review before main merge.

Reproduce with README.md PowerShell commands and inspect FEATURE_CHECKLIST.md,
QA_RESULTS.md and docs/evidence/. UI screenshots are in docs/evidence/screenshots/.
No merge into main is authorized by this PR; human team review is required.
