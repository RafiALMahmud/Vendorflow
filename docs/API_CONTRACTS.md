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
