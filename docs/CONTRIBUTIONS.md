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

## Developer 2 — Risk Intelligence & Admin Experience

No Developer 2-owned application, risk engine, workflow, review model, admin UI,
audit, or CI implementation is present in the fetched repository state as of
2026-10-17. Their contribution section must be completed by Developer 2 from
merged code and actual test evidence. Developer 1 did not implement or rewrite
the application state machine.

## Shared integration status

The verified-vendor snapshot contract is ready for Developer 2 consumption.
The full vendor submit -> admin request corrections -> vendor resubmit -> admin
approve journey remains untested because those modules are absent. The project
must not be described as fully complete until both role-based journeys and the
sequential review migration are integrated and tested together.
