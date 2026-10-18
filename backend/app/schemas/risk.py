"""Dev 2 input boundary; replace with the shared contract after Dev 1 review."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

DocumentType = Literal['trade_license', 'business_registration', 'tax_certificate', 'other']


class VerifiedField(BaseModel):
    raw_value: str | None = None
    confirmed_value: str | None = None
    review_status: Literal['unreviewed', 'confirmed', 'corrected'] = 'unreviewed'

    @property
    def verified_value(self) -> str | None:
        if self.review_status in {'confirmed', 'corrected'} and self.confirmed_value:
            return self.confirmed_value.strip() or None
        return None


class DocumentSnapshot(BaseModel):
    document_id: str
    document_type: DocumentType
    processing_status: Literal['uploaded', 'processing', 'processed', 'failed']
    fields: dict[str, VerifiedField] = Field(default_factory=dict)


class VendorSnapshot(BaseModel):
    vendor_id: str
    company_name: str
    documents: list[DocumentSnapshot] = Field(default_factory=list)


class RiskRules(BaseModel):
    model_config = ConfigDict(frozen=True)
    version: str = 'review-readiness-v1'
    required_documents: tuple[DocumentType, ...] = ('trade_license', 'business_registration')
    missing_document: int = Field(default=30, ge=0)
    expired_license: int = Field(default=25, ge=0)
    company_mismatch: int = Field(default=20, ge=0)
    missing_registration: int = Field(default=15, ge=0)
    unverified_field: int = Field(default=10, ge=0)


class Evidence(BaseModel):
    document_type: DocumentType
    document_id: str | None = None
    field_name: str | None = None


class Finding(BaseModel):
    code: str
    severity: Literal['warning', 'error']
    description: str
    deduction: int
    evidence: list[Evidence]


class RiskAssessment(BaseModel):
    score: int = Field(ge=0, le=100)
    level: Literal['low_review_priority', 'medium_review_priority', 'high_review_priority']
    findings: list[Finding]
    rules_version: str
    reference_date: date
