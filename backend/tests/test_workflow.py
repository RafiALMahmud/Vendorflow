from datetime import datetime, timedelta, timezone
from itertools import product

import pytest
from pydantic import ValidationError

from app.schemas.application import ApplicationStatus as S, ReviewDecision
from app.services.workflow import WorkflowError, WorkflowForbidden, plan_transition

LEGAL = {(S.DRAFT, S.SUBMITTED), (S.NEEDS_CORRECTION, S.RESUBMITTED)} | {
    (before, after) for before in (S.SUBMITTED, S.RESUBMITTED)
    for after in (S.APPROVED, S.REJECTED, S.NEEDS_CORRECTION)}


def transition(before=S.SUBMITTED, after=S.APPROVED, **overrides):
    values = dict(application_id='a', current=before, target=after,
                  actor_user_id='admin', actor_role='admin', owner_user_id='vendor',
                  now=datetime(2026, 10, 18, tzinfo=timezone.utc), note=' Check document ')
    values.update(overrides)
    return plan_transition(**values)


@pytest.mark.parametrize('before,after', list(product(S, S)))
def test_every_state_pair(before, after):
    vendor = after in {S.SUBMITTED, S.RESUBMITTED}
    identity = dict(actor_user_id='vendor', actor_role='vendor') if vendor else {}
    if (before, after) in LEGAL:
        event = transition(before, after, **identity)
        assert (event.before, event.after) == (before, after)
        assert event.note == 'Check document'
        assert event.application_id == 'a'
    else:
        with pytest.raises(WorkflowError):
            transition(before, after, **identity)


@pytest.mark.parametrize('role', ['vendor', 'anonymous', '', 'ADMIN'])
def test_non_admin_cannot_review(role):
    with pytest.raises(WorkflowForbidden):
        transition(actor_role=role)


@pytest.mark.parametrize('role,user', [('vendor', 'stranger'), ('admin', 'vendor'),
                                      ('anonymous', 'vendor')])
def test_submission_requires_owning_vendor(role, user):
    with pytest.raises(WorkflowForbidden):
        transition(S.DRAFT, S.SUBMITTED, actor_role=role, actor_user_id=user)


@pytest.mark.parametrize('target', [S.REJECTED, S.NEEDS_CORRECTION])
@pytest.mark.parametrize('note', ['', ' \n '])
def test_decision_requires_reason(target, note):
    with pytest.raises(WorkflowError):
        transition(after=target, note=note)


def test_double_review_and_naive_time_rejected():
    first = transition()
    with pytest.raises(WorkflowError):
        transition(before=first.after)
    with pytest.raises(WorkflowError):
        transition(now=datetime(2026, 10, 18))


def test_client_cannot_inject_identity_or_score():
    with pytest.raises(ValidationError):
        ReviewDecision(decision='approved', expected_version=1, actor_role='admin', score=100)


def test_audit_time_normalizes_to_utc_and_note_is_bounded():
    local_time = datetime(2026, 10, 18, 6, tzinfo=timezone(timedelta(hours=6)))
    assert transition(now=local_time).created_at == datetime(2026, 10, 18, tzinfo=timezone.utc)
    with pytest.raises(WorkflowError):
        transition(note='x' * 4001)


@pytest.mark.parametrize('decision', ['draft', 'submitted', 'resubmitted'])
def test_review_payload_only_accepts_human_decisions(decision):
    with pytest.raises(ValidationError):
        ReviewDecision(decision=decision, expected_version=0)
