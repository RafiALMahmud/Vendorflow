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
