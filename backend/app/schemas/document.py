from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.documents import DocumentType, ProcessingStatus, ReviewStatus


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    vendor_id: UUID
    document_type: DocumentType
    original_filename: str
    mime_type: str
    file_size: int
    processing_status: ProcessingStatus
    processing_error: str | None
    created_at: datetime
    updated_at: datetime


class ExtractedFieldResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    field_name: str
    raw_value: str | None
    normalized_value: str | None
    confirmed_value: str | None
    review_status: ReviewStatus
    extraction_method: str | None
    review_note: str | None
    created_at: datetime
    updated_at: datetime


EditableFieldName = Literal[
    "company_name",
    "registration_number",
    "license_number",
    "certificate_number",
    "issue_date",
    "expiry_date",
    "tax_identifier",
]


class ExtractedFieldReviewUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field_name: EditableFieldName
    confirmed_value: str = Field(min_length=1, max_length=2000)
    review_status: Literal["confirmed", "corrected"]

    @field_validator("confirmed_value")
    @classmethod
    def normalize_confirmed_value(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("confirmed_value cannot be blank")
        return normalized

    @model_validator(mode="after")
    def validate_normalized_date(self) -> "ExtractedFieldReviewUpdate":
        if self.field_name not in {"issue_date", "expiry_date"}:
            return self
        try:
            parsed = date.fromisoformat(self.confirmed_value)
        except ValueError as exc:
            raise ValueError(
                f"{self.field_name} must be a valid date in YYYY-MM-DD format"
            ) from exc
        if parsed.isoformat() != self.confirmed_value:
            raise ValueError(
                f"{self.field_name} must be a valid date in YYYY-MM-DD format"
            )
        return self


class ExtractedFieldsReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fields: list[ExtractedFieldReviewUpdate] = Field(min_length=1, max_length=7)

    @model_validator(mode="after")
    def reject_duplicate_fields(self) -> "ExtractedFieldsReviewRequest":
        names = [field.field_name for field in self.fields]
        if len(names) != len(set(names)):
            raise ValueError("Each field_name may be updated only once per request")
        return self
