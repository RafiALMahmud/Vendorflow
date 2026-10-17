from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

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
