# API reference

Interactive OpenAPI: http://localhost:8000/docs. All routes use /api/v1 and
snake_case JSON. Protected routes require Authorization: Bearer <access_token>.
Errors use a detail envelope. JWT roles are loaded from the database.

| Method | Path | Access |
|---|---|---|
| POST | /auth/register | Public, vendor only |
| POST | /auth/login | Public JSON email/password |
| GET | /auth/me | Authenticated principal |
| POST/GET/PATCH | /vendors/me | Own vendor profile |
| POST | /documents/upload | Vendor profile; multipart type/file |
| GET | /documents | Own document list |
| GET | /documents/{id} | Own metadata |
| GET | /documents/{id}/file | Own private original |
| GET/PATCH | /documents/{id}/extracted-fields | Own raw/verified field review |
| POST | /documents/{id}/retry | Owner; failed extraction only |
| POST | /applications | Owner; create/reuse active draft |
| GET | /applications/me | Own status/history |
| POST | /applications/{id}/submit | Owner draft -> submitted; idempotent repeat |
| POST | /applications/{id}/resubmit | Owner corrections -> resubmitted |
| GET | /admin/dashboard | Admin; DB counts |
| GET | /admin/applications | Admin; status/search/page/page_size |
| GET | /admin/applications/{id} | Admin; immutable evidence, findings and audit |
| GET | /admin/applications/{id}/risk | Admin; latest assessment |
| PATCH | /admin/applications/{id}/review | Admin human decision |
| GET | /admin/applications/{id}/documents/{doc_id}/file | Admin; original in saved case evidence |

Review body: {decision: approved|rejected|needs_correction, note: string,
expected_version: nonnegative integer}. Reject/correction require a nonblank note
up to 4000 characters. Extra role/score/identity fields are rejected. Stale version
or invalid transition is 409; missing/foreign owner object is 404; unauthenticated
is 401; role denial is 403; invalid input is 422.

Field review accepts confirmed/corrected values for company_name,
registration_number, license_number, certificate_number, tax_identifier,
issue_date and expiry_date. Confirmed must match the extracted candidate;
corrected must differ. Dates use YYYY-MM-DD. Raw OCR remains unchanged.

Detailed original D1 payloads and shared contract remain in API_CONTRACTS.md.
