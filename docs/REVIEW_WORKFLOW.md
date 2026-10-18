# Review workflow and persistence handoff

Implemented: pure `plan_transition` policy, typed transition event, vendor status
widget, admin review components, and tests. No production review API or database
write exists yet. This milestone does not establish persisted auditing, JWT RBAC,
or concurrent-review safety.

Allowed transitions:

```text
draft -> submitted
submitted -> needs_correction | approved | rejected
needs_correction -> resubmitted
resubmitted -> needs_correction | approved | rejected
```

Owning vendors alone submit/resubmit; admins alone review. The policy accepts
identity arguments only from a future server-loaded authenticated principal and
DB ownership query, never from JSON identity/role fields. Rejection and correction
require a trimmed nonempty note; notes are limited to 4000 characters. Timestamps
must be timezone-aware. All 36 state pairs are tested. A second decision against
a terminal state is invalid; this pure check alone cannot prevent DB races.

After Dev 1 merges identity/vendor migrations, add review models using the existing
`app.db.base.Base`, plus the next sequential migration. Preserve earlier revisions.
Proposed fields follow PROJECT_SPEC; additionally use a nonnegative integer
`version` for optimistic concurrency and a decision note in audit metadata.
Enforce one active application/vendor with a PostgreSQL partial unique index over
draft/submitted/needs_correction/resubmitted. Existing active draft creation should
return the same application; duplicate submission should return its existing
assessment without creating another audit event. Review of stale versions is 409.

In a DB transaction, lock the application (`SELECT ... FOR UPDATE`) and authorize
against the trusted principal, validate expected version/current state, then:

1. Submission: call Dev 1's `build_verified_vendor_snapshot(vendor_id, db)`, compute
   and append a versioned assessment; update status/timestamps/version.
2. Review: update status/reviewer/review timestamp/version with the human decision.
3. Append actor/application/action, before/after state, note, and UTC audit time.
4. Commit together, rolling back everything on any failure.

Do not add migrations before base schema merges. Add actual PostgreSQL transaction,
rollback, active-application uniqueness, and concurrent-review tests at integration.
