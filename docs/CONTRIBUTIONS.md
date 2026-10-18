# VendorFlow AI contributions

This file records implemented work only. It is not a claim that both role-based
journeys or the complete product have shipped.

## Developer 1 — Document Intelligence & Vendor Experience

Developer 1 implemented the current vertical slice across PostgreSQL,
SQLAlchemy/Alembic, FastAPI, React/TypeScript, tests, and local documentation:

- runnable backend/frontend baseline, environment configuration, CORS, health
  API, PostgreSQL session, and sequential migrations `0001`–`0005`;
- vendor-only public registration, Argon2 password hashing, expiring signed JWT
  access tokens, reusable vendor/admin role dependencies, and a local-only
  secure admin seed command;
- vendor profile create/read/update with database-enforced one-owner scoping;
- private PDF/JPG/JPEG/PNG ingestion with size, filename, MIME, signature, and
  structural validation plus generated storage keys and authorized downloads;
- real selectable-text PDF extraction using PyMuPDF and optional local Tesseract
  OCR for scans, with explicit processing states and sanitized failures;
- fictional parsing and unambiguous date normalization for six agreed fields;
- human confirmation/correction that preserves raw values and never marks OCR
  guesses verified automatically;
- typed, deterministic `build_verified_vendor_snapshot(vendor_id, db)` handoff;
- responsive vendor authentication, dashboard, profile, upload/list, document
  detail/download, and extraction-review screens backed by real APIs;
- PostgreSQL-backed authorization/integration tests, deterministic mocked-OCR
  tests, and a four-document fictional exact-match evaluation corpus.

Measured extraction evidence is intentionally narrow. In the recorded local
environment, the two digital PDFs produced 12/12 exact fields. Overall was
12/24 because Tesseract was unavailable and both OCR-dependent documents stayed
in the denominator. This is not a real-world OCR accuracy claim.

### CV-ready wording after merge

> Built a secure vendor onboarding and document-review vertical slice with
> FastAPI, PostgreSQL, Alembic, React, TypeScript, PyMuPDF, and optional
> Tesseract; enforced cross-vendor isolation and validated digital extraction on
> 2 fictional PDFs with 12/12 exact fields across 6 field types.

The sample size and fictional nature must remain attached to the metric. Do not
describe this as a trained AI model, fraud detection, commercial deployment, or
measured production performance.

## Developer 2 - Risk Intelligence & Admin Experience

Implemented pure explainable risk rules; explicit owning-vendor/admin workflow
policy; Application, RiskAssessmentRecord and AuditEvent on the shared ORM Base;
sequential migration 0006_review; authenticated application/admin APIs; immutable
submission evidence; atomic state/assessment/audit writes; PostgreSQL row locks,
optimistic review versions and active-application uniqueness; routed React review
and submission screens; GitHub Actions with isolated PostgreSQL service; and
integration, concurrency, authorization and browser verification.

## Combined integration evidence - 2026-10-18

172 backend tests and 24 frontend tests passed. PostgreSQL migrations from zero,
review downgrade/upgrade, schema consistency, dependency checks, ESLint and the
TypeScript/Vite build passed. A headless Edge browser completed vendor login,
draft/submit, admin correction, vendor resubmit, admin approve and denied vendor
access to the admin page with no browser runtime errors. Desktop/mobile evidence
is saved locally under ignored `.local/screenshots/`.

No trained model, real fraud determination, production readiness, or real OCR on
this machine is claimed. Tesseract is unavailable; digital PDF extraction is real,
and OCR paths are mocked in automated tests.


## 2026-10-19 completion work on feat/complete-vendorflow-mvp

The team leader authorized finishing both workstreams. Original D1 and D2 module
ownership/history above is preserved. This run added generic release-layout parser
fixes and certificate numbers, portable OCR verification/configuration, session
expiry, owner-only failed-extraction retry, case-scoped admin file access, decision
confirmation dialogs, Playwright browser acceptance, fresh setup scripts, CI and
release evidence. It did not claim the teammate's original work as new integration
work or rewrite their commits.

Current evidence supersedes historical counts/blocked OCR above: 182 backend tests,
27 frontend tests, two real browser scenarios, lint/build/migrations/fresh checkout
and all four CI jobs pass. The supplied four fictional PDFs match 23/23 fields,
including 6/6 actually OCR-read fields in the scan. This is a separate narrow
measurement from D1's original corpus; no real-world OCR/fraud claim is made.
