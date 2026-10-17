# VendorFlow API contracts

All endpoints are prefixed with `/api/v1`, accept and return JSON, and use the
error envelope `{"detail": ...}`. Examples below use fictional identities and
truncated placeholder tokens.

## Register a vendor

`POST /api/v1/auth/register`

```json
{
  "email": "vendor@example.com",
  "full_name": "Fictional Vendor",
  "password": "correct-horse-battery-staple"
}
```

Successful response: `201 Created`

```json
{
  "id": "10000000-0000-4000-8000-000000000001",
  "email": "vendor@example.com",
  "full_name": "Fictional Vendor",
  "role": "vendor",
  "created_at": "2026-10-17T08:30:00Z"
}
```

Public registration never accepts a role. Sending `"role": "admin"` returns
`422 Unprocessable Entity`; a duplicate normalized email returns `409 Conflict`.

## Log in

`POST /api/v1/auth/login`

```json
{
  "email": "vendor@example.com",
  "password": "correct-horse-battery-staple"
}
```

Successful response: `200 OK`

```json
{
  "access_token": "eyJ...signed-token-truncated",
  "token_type": "bearer",
  "expires_in": 1800
}
```

Unknown emails and incorrect passwords both return the same `401 Unauthorized`
response to avoid disclosing which accounts exist:

```json
{
  "detail": "Incorrect email or password"
}
```

## Read the authenticated user

`GET /api/v1/auth/me`

Request header:

```text
Authorization: Bearer eyJ...signed-token-truncated
```

Successful response: `200 OK`

```json
{
  "id": "10000000-0000-4000-8000-000000000001",
  "email": "vendor@example.com",
  "full_name": "Fictional Vendor",
  "role": "vendor",
  "created_at": "2026-10-17T08:30:00Z"
}
```

Missing, expired, malformed, or incorrectly signed tokens return:

```json
{
  "detail": "Could not validate credentials"
}
```

## Shared backend dependencies

Developer 2 should import authentication primitives from `app.core.auth`:

- `CurrentUser` or `get_current_user` for any authenticated user.
- `require_admin` for admin-only routes.
- `require_vendor` for vendor-only routes.
- `require_roles(...)` when a route intentionally accepts multiple roles.

The database user record is authoritative for roles. JWT claims identify the
user but do not grant a client-controlled role.

## Create the authenticated vendor's profile

`POST /api/v1/vendors/me`

```json
{
  "company_name": "Example Trading Ltd",
  "registration_number": "REG-001",
  "contact_email": "operations@example.com",
  "phone": "+880 1700-000000",
  "address": "100 Fictional Commerce Road, Dhaka"
}
```

Successful response: `201 Created`

```json
{
  "id": "20000000-0000-4000-8000-000000000001",
  "owner_user_id": "10000000-0000-4000-8000-000000000001",
  "company_name": "Example Trading Ltd",
  "registration_number": "REG-001",
  "contact_email": "operations@example.com",
  "phone": "+880 1700-000000",
  "address": "100 Fictional Commerce Road, Dhaka",
  "created_at": "2026-10-17T08:40:00Z",
  "updated_at": "2026-10-17T08:40:00Z"
}
```

The server takes `owner_user_id` from the bearer token. A second create attempt
returns `409 Conflict`; missing or invalid fields return `422 Unprocessable
Entity`. An admin receives `403 Forbidden` because profile management is a
vendor-only operation.

## Read the authenticated vendor's profile

`GET /api/v1/vendors/me`

The request uses the same bearer header as `/auth/me`. It returns the profile
shape above with `200 OK`, or `404 Not Found` when the authenticated vendor has
not created a profile:

```json
{
  "detail": "Vendor profile not found"
}
```

## Update the authenticated vendor's profile

`PATCH /api/v1/vendors/me`

Only changed fields need to be supplied:

```json
{
  "company_name": "Example Trading Updated",
  "phone": "+880 1711-111111"
}
```

Successful response: `200 OK`, with the complete updated profile. An empty
object, explicit `null`, unsupported field, blank required value, malformed
email, or unsupported phone characters returns `422 Unprocessable Entity`.
All three profile operations query by the authenticated `owner_user_id`, so one
vendor cannot read or update another vendor's record.

## Upload a private document

`POST /api/v1/documents/upload`

Content type: `multipart/form-data` with these fields:

- `document_type`: `trade_license`, `business_registration`, `tax_certificate`,
  or `other`.
- `file`: one PDF, JPG/JPEG, or PNG file.

PowerShell example (PowerShell 7+):

```powershell
$headers = @{ Authorization = "Bearer $accessToken" }
$form = @{
  document_type = "trade_license"
  file = Get-Item ".\fictional-license.pdf"
}
Invoke-RestMethod -Method Post `
  -Uri "http://localhost:8000/api/v1/documents/upload" `
  -Headers $headers `
  -Form $form
```

Successful response: `201 Created`

```json
{
  "id": "30000000-0000-4000-8000-000000000001",
  "vendor_id": "20000000-0000-4000-8000-000000000001",
  "document_type": "trade_license",
  "original_filename": "fictional-license.pdf",
  "mime_type": "application/pdf",
  "file_size": 1842,
  "processing_status": "processed",
  "processing_error": null,
  "created_at": "2026-10-17T09:00:00Z",
  "updated_at": "2026-10-17T09:00:00Z"
}
```

The response never exposes the private `storage_key`. The backend requires a
vendor profile, streams up to `DOCUMENT_MAX_FILE_SIZE_BYTES`, rejects path-like
filenames, validates the extension, declared MIME type, magic bytes, and actual
PDF/image structure, and stores a generated filename outside public directories.
Extraction then follows `uploaded` -> `processing` -> `processed` or `failed`.
A failure keeps the private upload and returns sanitized retry guidance in
`processing_error`; it never fabricates extracted fields.

Relevant errors use the normal `{ "detail": "..." }` envelope:

- `400` for empty, corrupt, unreadable, or path-like uploads.
- `401` for missing/invalid authentication; `403` for a non-vendor account.
- `409` when the vendor profile has not been created.
- `413` when the configured byte limit is exceeded.
- `415` for unsupported or mismatched file types/signatures.
- `422` for a missing multipart field or invalid `document_type`.

## List the authenticated vendor's documents

`GET /api/v1/documents`

Successful response: `200 OK`. The body is an array of the metadata shape above,
newest first. It is an empty array when the authenticated vendor has no files.
The ownership filter is applied in the database query.

## Read one owned document

`GET /api/v1/documents/{document_id}`

Successful response: `200 OK` with the metadata shape above. A missing document
or a document owned by another vendor returns the same `404` response:

```json
{
  "detail": "Document not found"
}
```

## Download one owned document

`GET /api/v1/documents/{document_id}/file`

Successful response: `200 OK` with the validated media type and an attachment
filename based on the safe original filename. Authorization is checked through
the vendor-owned database query before the private storage path is resolved.
Another vendor receives `404 Document not found`; a missing stored file returns
`404 Document file not found`.

## Read extracted fields

`GET /api/v1/documents/{document_id}/extracted-fields`

Successful response: `200 OK`

```json
[
  {
    "id": "40000000-0000-4000-8000-000000000001",
    "document_id": "30000000-0000-4000-8000-000000000001",
    "field_name": "expiry_date",
    "raw_value": "17 October 2027",
    "normalized_value": "2027-10-17",
    "confirmed_value": null,
    "review_status": "unreviewed",
    "extraction_method": "pdf_text",
    "review_note": null,
    "created_at": "2026-10-17T09:00:01Z",
    "updated_at": "2026-10-17T09:00:01Z"
  }
]
```

`extraction_method` is `pdf_text` when PyMuPDF found selectable text and
`tesseract_ocr` only when the local executable actually returned text. Ambiguous
or invalid dates have `normalized_value=null` and a human-readable `review_note`.
All candidates remain `unreviewed` with `confirmed_value=null`; this endpoint
does not verify OCR output. Ownership is enforced through the authenticated
vendor database query used for private file access.

## Review extracted fields

`PATCH /api/v1/documents/{document_id}/extracted-fields`

This vendor-only endpoint records an explicit human decision for one or more
existing extracted fields. A correct extracted candidate is submitted as
`confirmed`; a changed or previously unreadable value is submitted as
`corrected`. The server never promotes an OCR or parser guess automatically.

```json
{
  "fields": [
    {
      "field_name": "company_name",
      "confirmed_value": "Northstar Fictional Trading Ltd",
      "review_status": "confirmed"
    },
    {
      "field_name": "expiry_date",
      "confirmed_value": "2028-10-17",
      "review_status": "corrected"
    }
  ]
}
```

Successful response: `200 OK`. The response is the complete, freshly saved
field list in the same shape as `GET .../extracted-fields`:

```json
[
  {
    "id": "40000000-0000-4000-8000-000000000001",
    "document_id": "30000000-0000-4000-8000-000000000001",
    "field_name": "company_name",
    "raw_value": "Northstar Fictional Trading Ltd",
    "normalized_value": null,
    "confirmed_value": "Northstar Fictional Trading Ltd",
    "review_status": "confirmed",
    "extraction_method": "pdf_text",
    "review_note": null,
    "created_at": "2026-10-17T09:00:01Z",
    "updated_at": "2026-10-17T09:10:00Z"
  },
  {
    "id": "40000000-0000-4000-8000-000000000002",
    "document_id": "30000000-0000-4000-8000-000000000001",
    "field_name": "expiry_date",
    "raw_value": "17 October 2027",
    "normalized_value": "2027-10-17",
    "confirmed_value": "2028-10-17",
    "review_status": "corrected",
    "extraction_method": "pdf_text",
    "review_note": null,
    "created_at": "2026-10-17T09:00:01Z",
    "updated_at": "2026-10-17T09:10:00Z"
  }
]
```

`raw_value`, `normalized_value`, and extraction provenance remain unchanged by
review. Allowed field names are `company_name`, `registration_number`,
`license_number`, `issue_date`, `expiry_date`, and `tax_identifier`. Date
confirmations and corrections must be valid ISO `YYYY-MM-DD` dates. A
`confirmed` value must match the extracted candidate (the normalized value when
present, otherwise the raw value); a changed value must use `corrected`.

The request must contain one to six unique fields and rejects blank/null values,
unknown or non-extracted fields, unsupported statuses, extra properties, and
malformed JSON with `422 Unprocessable Entity`. The entire batch is validated
before any update is saved. Missing authentication returns `401`; another
vendor's document returns the same `404 Document not found` response as an
unknown document.
