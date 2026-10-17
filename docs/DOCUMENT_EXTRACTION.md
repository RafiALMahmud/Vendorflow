# Document text extraction

VendorFlow uses deterministic local tooling only. It does not train a model,
call a paid AI API, or treat OCR output as verified business information.

## Processing flow

1. Secure ingestion validates and stores a PDF, JPG/JPEG, or PNG file.
2. The database record starts as `uploaded` and changes to `processing`.
3. For PDFs, PyMuPDF reads selectable text first. If selectable text is present,
   OCR is not called.
4. Image-only PDFs are rendered page by page at 200 DPI. Rendered pages and
   uploaded images are passed to the local Tesseract executable through stdin.
5. Labeled values are parsed using transparent regular expressions for the
   fictional document templates.
6. The document finishes as `processed`, or as `failed` with a sanitized error
   and practical retry guidance.

The parser recognizes values only when these labels are actually present:

- `Company Name`
- `Registration Number` or `Reg No`
- `License Number` or `Licence Number`
- `Issue Date`
- `Expiry Date`, `Expiration Date`, or `Expires Date`
- `Tax Identifier`, `Tax ID`, or `TIN`

Every candidate retains its original `raw_value` and extraction method
(`pdf_text` or `tesseract_ocr`). Dates with an unambiguous format also receive an
ISO `normalized_value`. A numeric date such as `04/05/2026` remains unnormalized
and receives a `review_note` asking a human to confirm day/month order. Invalid
dates are similarly flagged.

All extracted fields start with `review_status=unreviewed` and
`confirmed_value=null`. OCR output and parser candidates are never promoted to
verified values automatically.

## Install Tesseract

See the official installation documentation:
<https://github.com/tesseract-ocr/tessdoc/blob/main/Installation.md>.

### Windows

The Tesseract project does not publish a current official Windows installer. Its
documentation links to third-party Windows builds, including the UB Mannheim
installer. Install English language data, then add the installation directory
to `PATH` or configure the executable explicitly:

```powershell
tesseract --version
tesseract --list-langs
```

If it is not on `PATH`, add this to the repository `.env` file:

```text
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
TESSERACT_LANGUAGE=eng
```

Restart FastAPI after changing `.env`. Do not place quotes around the `.env`
path. The exact installation directory may differ.

### Ubuntu/Debian

```bash
sudo apt update
sudo apt install tesseract-ocr tesseract-ocr-eng
tesseract --version
```

### macOS

```bash
brew install tesseract
tesseract --version
```

The official documentation also lists MacPorts as an option.

## Configuration

```text
TESSERACT_CMD=
TESSERACT_LANGUAGE=eng
TESSERACT_TIMEOUT_SECONDS=30
EXTRACTION_MAX_PDF_PAGES=20
```

- Leave `TESSERACT_CMD` empty to discover `tesseract` from `PATH`.
- The timeout applies to each OCR invocation.
- The PDF page limit bounds CPU and memory work.

## Failure and retry behavior

Missing Tesseract affects only documents that actually require OCR. A digital
PDF with selectable text still processes successfully without Tesseract.

For a missing executable, timeout, unreadable document, empty OCR result, or
unexpected safe failure, the document becomes `failed`; `processing_error`
explains whether to install/fix Tesseract, upload a clearer scan, upload an
unlocked PDF, shorten the PDF, or contact support. Internal stack traces,
document contents, tokens, and storage paths are not returned to clients.

There is no separate retry endpoint in the shared API contract. After correcting
the cause, upload the document again. The processing service itself clears stale
extracted candidates before each attempt so future retry orchestration is safe.

## Tests

Automated tests do not require a system Tesseract installation. They use:

- a generated fictional digital PDF for real PyMuPDF text extraction;
- a generated fictional scanned PNG and image-only PDF;
- mocked Tesseract output for deterministic OCR-path tests;
- parser/date normalization tests;
- PostgreSQL persistence, lifecycle, and cross-vendor access tests.

Run them from `backend`:

```powershell
..\.venv\Scripts\python.exe -m pytest tests\test_extraction.py
```

A real OCR smoke test should be run only when `tesseract --version` succeeds.
Use fictional input and confirm that the extraction method is `tesseract_ocr`;
do not claim a real OCR result when the executable is missing.

## Fictional extraction-quality corpus

The committed corpus lives in `backend/tests/fixtures/quality_documents/` and
contains no real company or personal data. Its exact expected values are in
`ground_truth.json`.

| Fixture | Kind | OCR required | Expected fields |
| --- | --- | ---: | ---: |
| `alpha-trade-license.pdf` | Selectable-text PDF | No | 6 |
| `beta-business-registration.pdf` | Selectable-text PDF | No | 6 |
| `gamma-tax-certificate.png` | Scanned PNG | Yes | 6 |
| `delta-license-scan.pdf` | Image-only PDF | Yes | 6 |

Every document has known fictional values for `company_name`,
`registration_number`, `license_number`, `issue_date`, `expiry_date`, and
`tax_identifier`. The generator is committed so the pack is reproducible:

```powershell
cd backend
..\.venv\Scripts\python.exe -m scripts.generate_extraction_quality_fixtures
```

The evaluator performs actual PyMuPDF extraction and invokes actual Tesseract
for scan-dependent fixtures when it is available:

```powershell
..\.venv\Scripts\python.exe -m scripts.evaluate_extraction_quality
```

For non-date fields, exact match compares the parsed `raw_value` with ground
truth. For unambiguously normalized dates, it compares `normalized_value` with
the expected ISO `YYYY-MM-DD` value. Case, whitespace, and punctuation are not
fuzzily matched. The metric is exactly:

```text
exactly_matched_fields / expected_fields
```

Extraction failures remain in the denominator. This prevents a missing OCR
runtime or unreadable document from inflating accuracy by silently shrinking
the sample.

## Measured result — 2026-10-17

Environment: Python 3.12.8, PyMuPDF 1.28.2, Windows. Tesseract was not installed
or discoverable on `PATH` and `TESSERACT_CMD` did not point to an executable.

Actual evaluator output summary:

```json
{
  "metric_definition": "exactly_matched_fields / expected_fields",
  "documents": {
    "total": 4,
    "successfully_evaluated": 2,
    "failed": 2
  },
  "overall": {
    "exact_matches": 12,
    "expected_fields": 24,
    "accuracy": 0.5
  },
  "failure_categories": {
    "ocr_unavailable": 2
  }
}
```

Per-field results use four expected samples per field:

| Field | Exact matches | Expected | Accuracy |
| --- | ---: | ---: | ---: |
| `company_name` | 2 | 4 | 50% |
| `registration_number` | 2 | 4 | 50% |
| `license_number` | 2 | 4 | 50% |
| `issue_date` | 2 | 4 | 50% |
| `expiry_date` | 2 | 4 | 50% |
| `tax_identifier` | 2 | 4 | 50% |

The selectable-text PDF subset measured 12/12 exact fields (100%, two
documents, two samples per field). This is a small synthetic evaluation, not a
claim about real-world documents. No real OCR accuracy number is available from
this environment: both OCR-required documents failed before producing text.
Install Tesseract and rerun the same command to obtain a real local OCR result.

The automated test substitutes known OCR text after exercising the real image
and scanned-PDF conversion paths. It reports 24/24 only to prove deterministic
parsing and metric calculation; that result must not be presented as measured
Tesseract accuracy.

## Developer 1 security and integration coverage

The backend suite covers these acceptance criteria without entering Developer
2 review/risk modules:

| Area | Coverage |
| --- | --- |
| Registration | Vendor-only public role, duplicate email, Argon2 hash, rejected `role=admin` |
| JWT | Missing, malformed, expired, wrong-signature tokens; injected role claim cannot override the database role |
| Isolation | Separate users, profiles, document metadata/files/fields, field edits, and verified snapshots |
| Upload validation | Unsupported MIME/extension, mismatched signature, oversize, empty, corrupt PDF/JPEG/PNG, traversal filenames |
| Extraction | Digital PDF, mocked image/scanned-PDF OCR, missing executable, ambiguous/invalid dates, corrupt inputs |
| Human verification | Unreviewed values remain untrusted, confirmations/corrections persist, raw values do not change |
| Snapshot | No documents, failed documents, corrected/unreviewed fields, deterministic ordering, cross-vendor exclusion |
| Error hygiene | Generic authentication errors, ownership-safe `404`, sanitized extraction failures and logs |

Unexpected extraction exceptions are deliberately logged without arbitrary
exception text or tracebacks because those strings can contain document-derived
content or private storage paths. Clients receive only the fixed safe retry
message.

## Reproducible verification commands

From `backend`:

```powershell
# Real quality evaluation; OCR runs only when installed.
..\.venv\Scripts\python.exe -m scripts.evaluate_extraction_quality

# Focused quality/security tests. OCR subprocess calls are mocked.
..\.venv\Scripts\python.exe -m pytest `
  tests/test_extraction_quality.py `
  tests/test_extraction.py `
  tests/test_auth.py

# Complete PostgreSQL-backed backend suite.
..\.venv\Scripts\python.exe -m pytest
```

From `frontend`:

```powershell
npm test -- --run
npm run lint
npm run build
```

Observed focused backend output before the final full regression run:

```text
27 passed, 1 warning in 2.04s
```

The warning is the existing Starlette TestClient/httpx deprecation warning; it
does not indicate a test failure. The final full-suite and frontend outputs are
recorded below after executing these commands.

Final observed command results:

```text
backend> ..\.venv\Scripts\python.exe -m pytest
78 passed, 1 warning in 6.52s

frontend> npm test -- --run
Test Files  8 passed (8)
Tests      16 passed (16)
Duration   1.94s

frontend> npm run lint
eslint .
exit code 0

frontend> npm run build
tsc -b && vite build
55 modules transformed
dist/index.html                  0.48 kB | gzip: 0.30 kB
dist/assets/index-DwcuYm14.css  18.94 kB | gzip: 4.47 kB
dist/assets/index-BJ0Cs4H5.js  299.18 kB | gzip: 92.09 kB
built in 2.04s

backend> ..\.venv\Scripts\python.exe -m compileall -q app scripts tests
exit code 0

backend> ..\.venv\Scripts\alembic.exe check
No new upgrade operations detected.

workspace> tesseract --version
TESSERACT_NOT_FOUND: real OCR smoke test skipped
```

There were no failing commands in the final run. The earlier absence of
Tesseract is recorded as an evaluation failure category and a smoke-test
limitation, not hidden or reported as OCR success.

## CI coordination and limitations

- No shared CI workflow was changed in this Developer 1 branch. Developer 2
  owns the shared CI integration and can add the documented offline commands.
- CI must run the mocked OCR tests and must not require Tesseract.
- A Tesseract-enabled smoke job may be optional and environment-specific.
- The corpus has four clean synthetic documents and is intentionally too small
  to represent production OCR quality, varied layouts, handwriting, damage, or
  multilingual documents.
- Docker remains optional and is not required by generation, evaluation, or
  tests.
