"""PostgreSQL-backed API tests using real JWT dependencies and Dev 1 documents."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import event, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth import create_access_token, hash_password
from app.models.identity import User, UserRole, Vendor
from app.models.review import Application, AuditEvent, RiskAssessmentRecord
from app.routers.admin import review
from app.schemas.application import ReviewDecision
from app.services import review_store
from tests.fixtures.synthetic_documents import synthetic_digital_pdf_bytes

PASSWORD_HASH = hash_password('Fictional-test-password-2026')


def add_user(db, role='vendor'):
    user = User(email=f'{uuid4().hex}@example.com', full_name='Fictional Reviewer',
                password_hash=PASSWORD_HASH, role=UserRole(role))
    db.add(user); db.flush()
    if role == 'vendor':
        db.add(Vendor(owner_user_id=user.id, company_name='Northstar Fictional Trading Ltd',
            registration_number='REG-001', contact_email=user.email, phone='+8801700000000',
            address='1 Fictional Street'))
        db.flush()
    return user


def headers(user):
    return {'Authorization': f'Bearer {create_access_token(user.id)[0]}'}


@pytest.fixture
def actors(db_session):
    return tuple(add_user(db_session, role) for role in ('vendor', 'vendor', 'admin'))


def draft(client, user):
    response = client.post('/api/v1/applications', headers=headers(user))
    assert response.status_code == 200, response.text
    return response.json()


def submitted(client, user):
    application = draft(client, user)
    result = client.post(f"/api/v1/applications/{application['id']}/submit", headers=headers(user))
    assert result.status_code == 200, result.text
    return result.json()


def test_full_document_submission_correction_resubmission_approval(client, db_session, actors):
    owner, _, admin = actors
    for kind in ('trade_license', 'business_registration'):
        upload = client.post('/api/v1/documents/upload', headers=headers(owner),
            data={'document_type': kind}, files={'file': ('fictional.pdf', synthetic_digital_pdf_bytes(), 'application/pdf')})
        assert upload.status_code == 201, upload.text
        doc_id = upload.json()['id']
        corrected = client.patch(f'/api/v1/documents/{doc_id}/extracted-fields', headers=headers(owner),
            json={'fields': [{'field_name': name, 'confirmed_value': value,
                              'review_status': 'confirmed' if name == 'company_name' else 'corrected'}
                for name, value in [('company_name', 'Northstar Fictional Trading Ltd'),
                                    ('registration_number', 'REG-001'), ('expiry_date', '2099-12-31')]]})
        assert corrected.status_code == 200, corrected.text
    application = submitted(client, owner)
    app_id = application['id']
    detail = client.get(f'/api/v1/admin/applications/{app_id}', headers=headers(admin))
    assert detail.status_code == 200, detail.text
    assert detail.json()['assessment']['score'] == 100
    assert len(detail.json()['documents']) == 2
    correction = client.patch(f'/api/v1/admin/applications/{app_id}/review', headers=headers(admin),
        json={'decision': 'needs_correction', 'note': 'Please check company address', 'expected_version': 1})
    assert correction.status_code == 200, correction.text
    assert correction.json()['application']['correction_note'] == 'Please check company address'
    resubmit = client.post(f'/api/v1/applications/{app_id}/resubmit', headers=headers(owner))
    assert resubmit.status_code == 200, resubmit.text
    assert resubmit.json()['version'] == 3
    approved = client.patch(f'/api/v1/admin/applications/{app_id}/review', headers=headers(admin),
        json={'decision': 'approved', 'note': 'Documents reviewed', 'expected_version': 3})
    assert approved.status_code == 200, approved.text
    body = approved.json()
    assert body['application']['status'] == 'approved'
    assert [e['action'] for e in body['audit_events']] == [
        'draft_created', 'submitted', 'needs_correction', 'resubmitted', 'approved']
    assert body['audit_events'][-1]['before'] == {'status': 'resubmitted', 'version': 3}
    assert db_session.scalar(select(func.count()).select_from(RiskAssessmentRecord)) == 2
    dashboard = client.get('/api/v1/admin/dashboard', headers=headers(admin)).json()
    assert dashboard['approved'] == 1 and dashboard['awaiting_review'] == 0


@pytest.mark.parametrize('path', ['/admin/dashboard', '/admin/applications',
    '/admin/applications/00000000-0000-0000-0000-000000000001',
    '/admin/applications/00000000-0000-0000-0000-000000000001/risk'])
def test_admin_reads_require_real_authenticated_admin(client, actors, path):
    owner, _, _ = actors
    assert client.get('/api/v1'+path).status_code == 401
    assert client.get('/api/v1'+path, headers=headers(owner)).status_code == 403


def test_isolation_idempotency_and_role_escalation(client, db_session, actors):
    owner, other, admin = actors
    first = draft(client, owner)
    assert draft(client, owner)['id'] == first['id']
    assert client.get('/api/v1/applications/me', headers=headers(other)).json() == []
    app_id = first['id']
    assert client.post(f'/api/v1/applications/{app_id}/submit', headers=headers(other)).status_code == 404
    assert client.post('/api/v1/applications', headers=headers(admin)).status_code == 403
    for _ in range(2):
        assert client.post(f'/api/v1/applications/{app_id}/submit', headers=headers(owner)).status_code == 200
    assert db_session.scalar(select(func.count()).select_from(RiskAssessmentRecord)) == 1
    assert db_session.scalar(select(func.count()).select_from(AuditEvent)) == 2
    payload = {'decision': 'approved', 'expected_version': 1}
    assert client.patch(f'/api/v1/admin/applications/{app_id}/review', json=payload).status_code == 401
    assert client.patch(f'/api/v1/admin/applications/{app_id}/review', headers=headers(owner), json=payload).status_code == 403
    assert client.patch(f'/api/v1/admin/applications/{app_id}/review', headers=headers(admin), json={**payload, 'score': 100}).status_code == 422


def test_notes_stale_decisions_filtering_and_terminal_state(client, actors):
    owner, _, admin = actors
    application = submitted(client, owner)
    url = f"/api/v1/admin/applications/{application['id']}/review"
    for decision in ('rejected', 'needs_correction'):
        assert client.patch(url, headers=headers(admin), json={
            'decision': decision, 'note': ' ', 'expected_version': 1}).status_code == 422
    rejected = client.patch(url, headers=headers(admin), json={
        'decision': 'rejected', 'note': 'Required documents absent', 'expected_version': 1})
    assert rejected.status_code == 200
    for version in (1, 2):
        assert client.patch(url, headers=headers(admin), json={
            'decision': 'approved', 'expected_version': version}).status_code == 409
    page = client.get('/api/v1/admin/applications?status=rejected&search=Northstar&page_size=1', headers=headers(admin)).json()
    assert page['total'] == 1 and len(page['items']) == 1
    assert client.get('/api/v1/admin/applications?status=invalid', headers=headers(admin)).status_code == 422
    assert client.get('/api/v1/admin/applications?page_size=101', headers=headers(admin)).status_code == 422


def test_assessment_failure_leaves_state_and_audit_unchanged(client, db_session, actors, monkeypatch):
    owner, _, _ = actors
    application = draft(client, owner)
    def broken(*args, **kwargs):
        raise RuntimeError('Simulated assessment failure')
    monkeypatch.setattr(review_store, 'assess_risk', broken)
    with pytest.raises(RuntimeError, match='Simulated'):
        client.post(f"/api/v1/applications/{application['id']}/submit", headers=headers(owner))
    db_session.expire_all()
    row = db_session.get(Application, UUID(application['id']))
    assert row.status == 'draft' and row.version == 0
    assert db_session.scalar(select(func.count()).select_from(AuditEvent)) == 1
    assert db_session.scalar(select(func.count()).select_from(RiskAssessmentRecord)) == 0


def test_database_constraint_prevents_multiple_active_drafts(db_session, actors):
    owner, _, _ = actors
    vendor = review_store.vendor_for(db_session, owner)
    db_session.add(Application(vendor_id=vendor.id))
    db_session.flush()
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(Application(vendor_id=vendor.id))
        db_session.flush()


def test_audit_write_failure_rolls_back_assessment_and_state(client, db_session, actors):
    owner, _, _ = actors
    application = draft(client, owner)
    row = db_session.get(Application, UUID(application['id']))
    def refuse_audit(*args):
        raise RuntimeError('Simulated audit persistence failure')
    event.listen(AuditEvent, 'before_insert', refuse_audit)
    try:
        with pytest.raises(RuntimeError, match='audit persistence'), db_session.begin_nested():
            review_store.transition(db_session, row, owner, review_store.ApplicationStatus.SUBMITTED)
    finally:
        event.remove(AuditEvent, 'before_insert', refuse_audit)
    db_session.expire_all()
    assert row.status == 'draft' and row.version == 0
    assert db_session.scalar(select(func.count()).select_from(RiskAssessmentRecord)) == 0
    assert db_session.scalar(select(func.count()).select_from(AuditEvent)) == 1


def test_concurrent_admin_decisions_have_one_winner(db_session):
    # Separate committed rows/sessions are necessary to exercise real PostgreSQL locks.
    engine = db_session.get_bind().engine
    with Session(engine) as db:
        owner = add_user(db)
        admin = add_user(db, 'admin')
        vendor = review_store.vendor_for(db, owner)
        application = Application(vendor_id=vendor.id, status='submitted', version=1,
                                  submitted_at=datetime.now(timezone.utc))
        db.add(application); db.flush()
        app_id, admin_id, owner_id = application.id, admin.id, owner.id
        db.commit()
    barrier = Barrier(2)
    def decide(decision):
        with Session(engine) as db:
            admin = db.get(User, admin_id)
            barrier.wait(timeout=10)
            try:
                review(app_id, ReviewDecision(decision=decision, note='Human review', expected_version=1), db, admin)
                return 200
            except HTTPException as exc:
                return exc.status_code
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(decide, ['approved', 'rejected']))
        assert sorted(results) == [200, 409]
        with Session(engine) as db:
            assert db.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.application_id == app_id)) == 1
            assert db.get(Application, app_id).version == 2
    finally:
        with Session(engine) as db:
            for user_id in (owner_id, admin_id):
                db.delete(db.get(User, user_id))
            db.commit()
