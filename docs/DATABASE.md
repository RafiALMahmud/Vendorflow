# Database and migrations

One SQLAlchemy Base registers users, vendors, documents, extracted_fields,
applications, risk_assessments and audit_events. User/vendor/document foreign keys
are reused; there is no shadow authentication schema.

| Tables | Owner / purpose |
|---|---|
| users, vendors | D1: Argon2 identities and one vendor profile per user |
| documents, extracted_fields | D1: private file metadata and raw/verified fields |
| applications | D2: status, version, submit/review times and reviewer |
| risk_assessments | D2: immutable score/findings/rules version and evidence snapshot |
| audit_events | D2: actor/action/time/note and before/after state/version |

The existing linear migration chain 0001 -> 0002 -> 0003 -> 0004 -> 0005 ->
0006_review is preserved. Certificate-number support uses existing string field
storage; it needs no speculative migration. alembic check must show no schema drift.

A partial unique PostgreSQL index prevents multiple active applications/vendor.
Draft creation serializes on the vendor; submit/resubmit serializes on the owning
vendor/application; admin review locks the application and checks expected_version.
Audit endpoints do not offer edit/delete actions. Audit, assessment and state
updates commit together; rollback and concurrent-review tests exercise PostgreSQL.

Local setup creates its own SCRAM-authenticated cluster on 55432 with a cluster
admin and a separate application role. Development, disposable test and browser
QA DBs have distinct names. Never run pytest or downgrade commands on real data.
Fresh upgrade and rollback evidence is recorded in QA_RESULTS.md.
