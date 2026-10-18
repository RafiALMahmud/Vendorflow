"""Pure policy only. Call with server-loaded identity/state, never request identity.

Persistence adapter must lock/version-check the application and persist state,
fresh assessment on submit/resubmit, and this event in one DB transaction.
"""

from datetime import datetime, timezone

from app.schemas.application import ApplicationStatus as Status, TransitionEvent


class WorkflowError(ValueError):
    pass


class WorkflowForbidden(PermissionError):
    pass


def plan_transition(*, application_id: str, current: Status, target: Status,
                    actor_user_id: str, actor_role: str, owner_user_id: str,
                    now: datetime, note: str = '') -> TransitionEvent:
    vendor_action = target in {Status.SUBMITTED, Status.RESUBMITTED}
    if vendor_action:
        if actor_role != 'vendor' or actor_user_id != owner_user_id:
            raise WorkflowForbidden('Only the owning vendor may submit.')
    elif actor_role != 'admin':
        raise WorkflowForbidden('Administrator access required.')
    allowed = {
        Status.DRAFT: {Status.SUBMITTED},
        Status.SUBMITTED: {Status.NEEDS_CORRECTION, Status.APPROVED, Status.REJECTED},
        Status.NEEDS_CORRECTION: {Status.RESUBMITTED},
        Status.RESUBMITTED: {Status.NEEDS_CORRECTION, Status.APPROVED, Status.REJECTED},
    }
    if target not in allowed.get(current, set()):
        raise WorkflowError(f'Cannot transition {current} to {target}.')
    note = note.strip()
    if target in {Status.REJECTED, Status.NEEDS_CORRECTION} and not note:
        raise WorkflowError('A reason is required for rejection or correction.')
    if len(note) > 4000:
        raise WorkflowError('Note exceeds 4000 characters.')
    if now.tzinfo is None or now.utcoffset() is None:
        raise WorkflowError('An aware timestamp is required.')
    return TransitionEvent(actor_user_id=actor_user_id, application_id=application_id,
                           action=target.value, before=current, after=target,
                           note=note, created_at=now.astimezone(timezone.utc))
