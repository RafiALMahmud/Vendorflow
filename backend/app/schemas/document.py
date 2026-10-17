from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.documents import DocumentType, ProcessingStatus


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    vendor_id: UUID
    document_type: DocumentType
    original_filename: str
    mime_type: str
    file_size: int
    processing_status: ProcessingStatus
    created_at: datetime
    updated_at: datetime
