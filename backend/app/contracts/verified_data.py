from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


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

    model_config = ConfigDict(frozen=True, extra="forbid")

    raw_value: str | None = None
    confirmed_value: str | None = None
    review_status: ReviewStatus

    @model_validator(mode="after")
    def require_value_for_completed_review(self) -> "VerifiedFieldSnapshot":
        if (
            self.review_status in {ReviewStatus.CONFIRMED, ReviewStatus.CORRECTED}
            and self.confirmed_value is None
        ):
            raise ValueError(
                "confirmed_value is required when review_status is confirmed or corrected"
            )
        if (
            self.review_status == ReviewStatus.UNREVIEWED
            and self.confirmed_value is not None
        ):
            raise ValueError(
                "confirmed_value must be null when review_status is unreviewed"
            )
        return self

    @property
    def verified_value(self) -> str | None:
        if self.review_status not in {ReviewStatus.CONFIRMED, ReviewStatus.CORRECTED}:
            return None
        return self.confirmed_value


class VerifiedDocumentSnapshot(BaseModel):
    """Stable document evidence consumed by review-side services."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    document_id: UUID
    document_type: DocumentType
    processing_status: ProcessingStatus
    fields: dict[str, VerifiedFieldSnapshot] = Field(default_factory=dict)


class VerifiedVendorSnapshot(BaseModel):
    """Version 1 handoff from document extraction to review-side services."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    vendor_id: UUID
    company_name: str = Field(min_length=1)
    documents: tuple[VerifiedDocumentSnapshot, ...] = ()
