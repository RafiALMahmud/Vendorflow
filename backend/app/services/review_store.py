from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.identity import User, Vendor
from app.models.review import Application, AuditEvent, RiskAssessmentRecord
from app.schemas.application import ApplicationStatus
from app.schemas.risk import VendorSnapshot
from app.services.document_access import build_verified_vendor_snapshot
from app.services.risk_engine import assess_risk
from app.services.workflow import WorkflowError, WorkflowForbidden, plan_transition

ACTIVE = ('draft', 'submitted', 'needs_correction', 'resubmitted')


def vendor_for(db: Session, user: User, lock=False) -> Vendor:
    query = select(Vendor).where(Vendor.owner_user_id == user.id)
    if lock:
        query = query.with_for_update()
    vendor = db.scalar(query)
    if vendor is None:
        raise HTTPException(404, 'Create your vendor profile first')
    return vendor


def owned_application(db: Session, app_id: UUID, vendor: Vendor) -> Application:
    application = db.scalar(select(Application).where(
        Application.id == app_id, Application.vendor_id == vendor.id).with_for_update())
    if application is None:
        raise HTTPException(404, 'Application not found')
    return application


def latest_assessment(db: Session, app_id: UUID):
    return db.scalar(select(RiskAssessmentRecord).where(
        RiskAssessmentRecord.application_id == app_id).order_by(
            RiskAssessmentRecord.assessed_at.desc(), RiskAssessmentRecord.id.desc()).limit(1))


def application_json(db: Session, application: Application) -> dict:
    vendor = db.get(Vendor, application.vendor_id)
    return dict(id=str(application.id), vendor_id=str(application.vendor_id),
                company_name=vendor.company_name, status=application.status,
                version=application.version, submitted_at=application.submitted_at,
                reviewed_at=application.reviewed_at, correction_note=application.correction_note)


def assessment_json(record: RiskAssessmentRecord | None):
    if record is None:
        return None
    return dict(score=record.score, level=record.level, findings=record.findings_json,
                rules_version=record.rules_version, assessed_at=record.assessed_at)


def case_json(db: Session, application: Application) -> dict:
    assessment = latest_assessment(db, application.id)
    # Display the evidence used at submission, preserved even if vendor edits later.
    snapshot = assessment.snapshot_json if assessment else {'documents': []}
    events = db.scalars(select(AuditEvent).where(AuditEvent.application_id == application.id)
                        .order_by(AuditEvent.created_at, AuditEvent.id)).all()
    return dict(application=application_json(db, application), assessment=assessment_json(assessment),
                documents=snapshot['documents'], audit_events=[dict(
                    id=str(event.id), action=event.action, actor_user_id=event.actor_user_id,
                    created_at=event.created_at, note=event.note,
                    before=event.before_json, after=event.after_json) for event in events])


def transition(db: Session, application: Application, user: User,
               target: ApplicationStatus, note: str = ''):
    vendor = db.get(Vendor, application.vendor_id)
    now = datetime.now(timezone.utc)
    try:
        event = plan_transition(application_id=str(application.id),
            current=ApplicationStatus(application.status), target=target,
            actor_user_id=str(user.id), actor_role=user.role.value,
            owner_user_id=str(vendor.owner_user_id), now=now, note=note)
    except WorkflowForbidden as exc:
        raise HTTPException(403, str(exc)) from exc
    except WorkflowError as exc:
        raise HTTPException(422 if 'reason' in str(exc) else 409, str(exc)) from exc
    previous_version = application.version
    if target in {ApplicationStatus.SUBMITTED, ApplicationStatus.RESUBMITTED}:
        snapshot = build_verified_vendor_snapshot(vendor.id, db)
        assessment = assess_risk(VendorSnapshot.model_validate(snapshot.model_dump(mode='json')), now.date())
        db.add(RiskAssessmentRecord(application_id=application.id, score=assessment.score,
            level=assessment.level, findings_json=[f.model_dump(mode='json') for f in assessment.findings],
            rules_version=assessment.rules_version, snapshot_json=snapshot.model_dump(mode='json'),
            assessed_at=now))
        application.submitted_at = now
        application.reviewed_at = None
        application.reviewer_user_id = None
        application.correction_note = None
    else:
        application.reviewed_at = now
        application.reviewer_user_id = user.id
        application.correction_note = event.note if target == ApplicationStatus.NEEDS_CORRECTION else None
    application.status = target.value
    application.version += 1
    db.add(AuditEvent(application_id=application.id, actor_user_id=user.id,
        action=event.action, before_json={'status': event.before.value, 'version': previous_version},
        after_json={'status': event.after.value, 'version': application.version},
        note=event.note, created_at=now))
    # Caller commits the state, assessment and audit event in the same transaction.
    db.flush()
