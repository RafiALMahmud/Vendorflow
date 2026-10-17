from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DocumentType(StrEnum):
    TRADE_LICENSE = "trade_license"
    BUSINESS_REGISTRATION = "business_registration"
    TAX_CERTIFICATE = "tax_certificate"
    OTHER = "other"


class ProcessingStatus(StrEnum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class ReviewStatus(StrEnum):
    UNREVIEWED = "unreviewed"
    CONFIRMED = "confirmed"
    CORRECTED = "corrected"


class VerifiedFieldSnapshot(BaseModel):
    """An extracted field and the vendor's review decision.

    Consumers must use ``verified_value`` instead of trusting OCR output. A raw
    value is evidence for manual review only until the vendor confirms or
    corrects it.
    """

    model_config = ConfigDict(frozen=True)

    raw_value: str | None = None
    confirmed_value: str | None = None
    review_status: ReviewStatus

    @property
    def verified_value(self) -> str | None:
        if self.review_status not in {ReviewStatus.CONFIRMED, ReviewStatus.CORRECTED}:
            return None
        return self.confirmed_value


class VerifiedDocumentSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    document_id: UUID
    document_type: DocumentType
    processing_status: ProcessingStatus
    fields: dict[str, VerifiedFieldSnapshot] = Field(default_factory=dict)


class VerifiedVendorSnapshot(BaseModel):
    """Version 1 handoff from document extraction to review-side services."""

    model_config = ConfigDict(frozen=True)

    vendor_id: UUID
    company_name: str = Field(min_length=1)
    documents: tuple[VerifiedDocumentSnapshot, ...] = ()
