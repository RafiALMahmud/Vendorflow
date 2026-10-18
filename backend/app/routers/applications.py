from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import require_vendor
from app.db.session import get_db
from app.models.identity import User
from app.models.review import Application, AuditEvent
from app.schemas.application import ApplicationStatus, ApplicationView
from app.services.review_store import ACTIVE, application_json, owned_application, transition, vendor_for

router = APIRouter(prefix='/applications', tags=['applications'])
DB = Annotated[Session, Depends(get_db)]
VendorUser = Annotated[User, Depends(require_vendor)]


@router.post('', response_model=ApplicationView)
def create_application(db: DB, user: VendorUser):
    # Serializes duplicate creates for this vendor before checking active uniqueness.
    vendor = vendor_for(db, user, lock=True)
    existing = db.scalar(select(Application).where(
        Application.vendor_id == vendor.id, Application.status.in_(ACTIVE)))
    if existing:
        return application_json(db, existing)
    application = Application(vendor_id=vendor.id, status='draft', version=0)
    db.add(application)
    db.flush()
    db.add(AuditEvent(application_id=application.id, actor_user_id=user.id, action='draft_created',
        before_json={}, after_json={'status': 'draft', 'version': 0}, note='', created_at=datetime.now(timezone.utc)))
    db.commit()
    return application_json(db, application)


@router.get('/me', response_model=list[ApplicationView])
def my_applications(db: DB, user: VendorUser):
    vendor = vendor_for(db, user)
    return [application_json(db, row) for row in db.scalars(select(Application)
        .where(Application.vendor_id == vendor.id).order_by(Application.created_at.desc()))]


def submit(db: Session, user: User, app_id: UUID, target: ApplicationStatus):
    vendor = vendor_for(db, user, lock=True)
    application = owned_application(db, app_id, vendor)
    if application.status == target.value:
        return application_json(db, application)
    transition(db, application, user, target)
    db.commit()
    return application_json(db, application)


@router.post('/{app_id}/submit', response_model=ApplicationView)
def submit_application(app_id: UUID, db: DB, user: VendorUser):
    return submit(db, user, app_id, ApplicationStatus.SUBMITTED)


@router.post('/{app_id}/resubmit', response_model=ApplicationView)
def resubmit_application(app_id: UUID, db: DB, user: VendorUser):
    return submit(db, user, app_id, ApplicationStatus.RESUBMITTED)
