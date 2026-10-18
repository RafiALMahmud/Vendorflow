# Proposed Dev 2 integration contract

These routes are **not implemented or mounted** in the baseline. All use `/api/v1`,
server-side JWT authentication and DB sessions owned by Dev 1, snake_case JSON,
and `{ "detail": "..." }` errors. No alternate authentication is introduced.

| Method | Path | Access/result |
| --- | --- | --- |
| POST | /applications | Vendor; existing/new own active draft |
| GET | /applications/me | Vendor; own applications |
| POST | /applications/{id}/submit | Owning vendor; submit draft |
| POST | /applications/{id}/resubmit | Owning vendor; resubmit corrections |
| GET | /admin/dashboard | Admin; total, awaiting_review, approved, rejected, needs_correction counts |
| GET | /admin/applications | Admin; status/search/page/page_size filters |
| GET | /admin/applications/{id} | Admin; case detail including latest assessment, documents and audit_events |
| GET | /admin/applications/{id}/risk | Admin; latest versioned assessment |
| PATCH | /admin/applications/{id}/review | Admin; human decision |

Queue returns `{items, total, page, page_size}`, page starts at 1, default page size
20, maximum 100. Validate status and bound search length before querying. Awaiting
review means submitted/resubmitted. Counts come from DB, never fixture fallbacks.
Case detail fields are declared in `frontend/src/features/applications/types.ts`.
Application includes `version`, `company_name`, nullable `submitted_at`, and status.

Review body: `{decision: "approved" | "rejected" | "needs_correction", note: string,
expected_version: integer}`. Extra identity/score fields are rejected. Return updated
case detail; stale version or invalid transition is 409, missing note/invalid input
422, missing login 401, nonadmin 403, missing/foreign vendor resource 404.

The frontend factory `createReviewApi(authenticatedFetch, baseUrl)` injects Dev 1's
future authenticated transport. It performs no token storage. Admin and vendor
components remain unmounted until identity, API and shared router integration are
owner-reviewed. Fixtures exist only in tests. Reload is required after failed review
to avoid repeating a stale decision. Vendor callbacks must refresh application state.

Smallest Dev 1 dependencies: shared snapshot typed contract and builder; real
User/Vendor model identifiers; authenticated current-user/admin dependencies; base
identity migrations; shared authenticated fetch/context and router mounting point.
