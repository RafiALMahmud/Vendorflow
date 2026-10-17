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
