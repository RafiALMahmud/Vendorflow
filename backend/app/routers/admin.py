from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import require_admin
from app.db.session import get_db
from app.models.identity import User, Vendor
from app.models.review import Application
from app.models.documents import Document
from app.core.config import get_settings
from app.services.document_storage import resolve_storage_path
from app.schemas.application import ApplicationStatus, ReviewDecision, CaseView, QueueView, DashboardView, AssessmentView
from app.services.review_store import application_json, assessment_json, case_json, latest_assessment, transition

router = APIRouter(prefix='/admin', tags=['admin'], dependencies=[Depends(require_admin)])
DB = Annotated[Session, Depends(get_db)]
AdminUser = Annotated[User, Depends(require_admin)]


@router.get('/dashboard', response_model=DashboardView)
def dashboard(db: DB):
    counts = dict(db.execute(select(Application.status, func.count()).group_by(Application.status)).all())
    return dict(total=sum(counts.values()), awaiting_review=counts.get('submitted', 0)+counts.get('resubmitted', 0),
        approved=counts.get('approved', 0), rejected=counts.get('rejected', 0), needs_correction=counts.get('needs_correction', 0))


@router.get('/applications', response_model=QueueView)
def queue(db: DB, status: str = '', search: Annotated[str, Query(max_length=200)] = '',
          page: Annotated[int, Query(ge=1)] = 1, page_size: Annotated[int, Query(ge=1, le=100)] = 20):
    if status and status not in {s.value for s in ApplicationStatus}:
        raise HTTPException(422, 'Unknown application status')
    filters = []
    if status:
        filters.append(Application.status == status)
    if search.strip():
        filters.append(Vendor.company_name.icontains(search.strip(), autoescape=True))
    query = select(Application).join(Vendor).where(*filters)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    items = db.scalars(query.order_by(Application.created_at.desc(), Application.id)
                       .offset((page-1)*page_size).limit(page_size)).all()
    return dict(items=[application_json(db, row) for row in items], total=total, page=page, page_size=page_size)


def find(db: Session, app_id: UUID, lock=False):
    query = select(Application).where(Application.id == app_id)
    if lock:
        query = query.with_for_update()
    application = db.scalar(query)
    if application is None:
        raise HTTPException(404, 'Application not found')
    return application


@router.get('/applications/{app_id}', response_model=CaseView)
def detail(app_id: UUID, db: DB):
    return case_json(db, find(db, app_id))


@router.get('/applications/{app_id}/risk', response_model=AssessmentView)
def risk(app_id: UUID, db: DB):
    find(db, app_id)
    assessment = latest_assessment(db, app_id)
    if assessment is None:
        raise HTTPException(404, 'No assessment yet')
    return assessment_json(assessment)


@router.get('/applications/{app_id}/documents/{document_id}/file', response_class=FileResponse)
def evidence_file(app_id: UUID, document_id: UUID, db: DB):
    application = find(db, app_id)
    assessment = latest_assessment(db, app_id)
    if assessment is None or not any(str(document_id) == doc['document_id']
                                     for doc in assessment.snapshot_json['documents']):
        raise HTTPException(404, 'Document is not evidence for this application')
    document = db.get(Document, document_id)
    if document is None or document.vendor_id != application.vendor_id:
        raise HTTPException(404, 'Document not found')
    try:
        path = resolve_storage_path(document.storage_key, get_settings())
    except FileNotFoundError:
        raise HTTPException(404, 'Document file not found') from None
    return FileResponse(path, media_type=document.mime_type, filename=document.original_filename,
                        content_disposition_type='attachment', headers={
                            'Cache-Control': 'private, no-store', 'X-Content-Type-Options': 'nosniff'})


@router.patch('/applications/{app_id}/review', response_model=CaseView)
def review(app_id: UUID, payload: ReviewDecision, db: DB, user: AdminUser):
    application = find(db, app_id, lock=True)
    if application.version != payload.expected_version:
        raise HTTPException(409, 'Application changed. Reload before reviewing.')
    transition(db, application, user, ApplicationStatus(payload.decision), payload.note)
    db.commit()
    return case_json(db, application)
