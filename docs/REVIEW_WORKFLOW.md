# Persisted review workflow

Allowed transitions are enforced by pure policy and secure API services:

```text
draft -> submitted
submitted -> needs_correction | approved | rejected
needs_correction -> resubmitted
resubmitted -> needs_correction | approved | rejected
```

Only authenticated owning vendors submit/resubmit; only DB-authorized admins
review. Client role, actor, score and arbitrary status are not accepted review
inputs. Rejection/correction require a trimmed note (maximum 4000 characters).

Application, RiskAssessmentRecord and AuditEvent use the existing ORM Base and
identity foreign keys. Sequential migration 0006_review follows D1's 0005.
A PostgreSQL partial unique index enforces one active application per vendor.
Draft creation locks the vendor and returns an existing active application;
repeated submit/resubmit in the same resulting state is idempotent.

Submission locks the owning vendor/application, reads the shared verified snapshot,
computes a fresh deterministic assessment and persists immutable evidence, state,
version and audit event in one transaction. Each resubmission preserves assessment
history. UTC timestamps are used. Rules never automatically approve/reject.

Review locks the application and compares expected_version with the stored version.
It validates the transition and note, then atomically updates reviewer/time/state/
version and appends before/after audit metadata. A stale or terminal review returns
409. Concurrent PostgreSQL review tests confirm exactly one decision and audit
write succeeds when two reviewers submit the same expected version.

The admin UI requires a case reload after failed review and displays the assessment's
submission evidence rather than mutable current document fields. Server-side roles
and ownership remain authoritative regardless of browser controls.
