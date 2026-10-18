from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from app.contracts.verified_data import VerifiedDocumentSnapshot


class ApplicationStatus(StrEnum):
    DRAFT = 'draft'
    SUBMITTED = 'submitted'
    NEEDS_CORRECTION = 'needs_correction'
    RESUBMITTED = 'resubmitted'
    APPROVED = 'approved'
    REJECTED = 'rejected'


class ReviewDecision(BaseModel):
    model_config = ConfigDict(extra='forbid')
    decision: Literal['approved', 'rejected', 'needs_correction']
    note: str = Field(default='', max_length=4000)
    expected_version: int = Field(ge=0)


class TransitionEvent(BaseModel):
    actor_user_id: str
    application_id: str
    action: str
    before: ApplicationStatus
    after: ApplicationStatus
    note: str
    created_at: datetime


class ApplicationView(BaseModel):
    id: UUID
    vendor_id: UUID
    company_name: str
    status: ApplicationStatus
    version: int
    submitted_at: datetime | None
    reviewed_at: datetime | None
    correction_note: str | None


class AssessmentView(BaseModel):
    score: int = Field(ge=0, le=100)
    level: str
    findings: list[dict]
    rules_version: str
    assessed_at: datetime


class AuditView(BaseModel):
    id: UUID
    action: str
    actor_user_id: UUID | None
    created_at: datetime
    note: str
    before: dict
    after: dict


class CaseView(BaseModel):
    application: ApplicationView
    assessment: AssessmentView | None
    documents: list[VerifiedDocumentSnapshot]
    audit_events: list[AuditView]


class QueueView(BaseModel):
    items: list[ApplicationView]
    total: int
    page: int
    page_size: int


class DashboardView(BaseModel):
    total: int
    awaiting_review: int
    approved: int
    rejected: int
    needs_correction: int
