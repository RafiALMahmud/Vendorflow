# Fictional acceptance demonstration

Use only backend/tests/fixtures/vendorflow_qa documents. They are not valid legal,
registration or tax documents. The deterministic reference date is 2026-10-19.

1. Register a vendor in the UI and set company NORTHSTAR TRADING LTD and
   registration REG-2026-0042. Save and edit the profile to verify persistence.
2. Upload 01 as trade_license, 02 as business_registration and 03 as tax_certificate.
   Inspect raw values and confirm each field. Dates are normalized separately.
3. In Applications, create a draft and submit. The fully confirmed positive
   fixture set scores 100 under the documented v1 policy.
4. Sign in as a locally seeded admin, open the case, inspect findings/evidence and
   download the original. Request correction with a note and confirm the dialog.
5. Vendor observes the note, corrects a field and resubmits. Admin inspects the
   new evidence, approves with a confirmation dialog, and checks persisted audit.
6. Register a separate vendor with company NORTHSTAR TRADING LTD and registration
   REG-2026-0099. Upload 04 only. Confirm actual OCR fields for EASTBRIDGE LOGISTICS
   LTD after inspection. The verified case scores 25: missing business registration
   (30), expired license (25), company mismatch (20). It remains submitted/resubmitted
   until a human decides. Unverified OCR alone must not assert expiry/mismatch.
7. Check rejection requires a note, access to the other vendor's IDs returns 404,
   and vendor access to admin APIs returns 403. Confirm counts and audit reflect
   the final state. Native dialogs support keyboard cancellation.

Automated browser commands and setup are in README.md. The positive and negative
Playwright scenarios perform UI registration/profile editing/uploads/verification,
correction/resubmission, approval/rejection, original download, mobile layout,
logout and API ownership checks against real PostgreSQL and Tesseract. Real status
and per-file field results are in QA_RESULTS.md and evidence/ocr-results.json.
