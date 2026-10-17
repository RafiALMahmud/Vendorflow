from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.auth import require_vendor
from app.core.config import get_settings
from app.db.session import get_db
from app.models.documents import Document, DocumentType, ProcessingStatus
from app.models.identity import User, Vendor
from app.schemas.document import DocumentResponse
from app.services.document_storage import (
    UploadValidationError,
    delete_stored_file,
    resolve_storage_path,
    store_validated_upload,
)

router = APIRouter(prefix="/documents", tags=["documents"])
VendorUser = Annotated[User, Depends(require_vendor)]
Database = Annotated[Session, Depends(get_db)]


def owned_document_query(document_id: UUID, current_user: User):
    return (
        select(Document)
        .join(Vendor, Document.vendor_id == Vendor.id)
        .where(Document.id == document_id, Vendor.owner_user_id == current_user.id)
    )


def get_owned_document(
    document_id: UUID,
    current_user: User,
    db: Session,
) -> Document:
    document = db.scalar(owned_document_query(document_id, current_user))
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    current_user: VendorUser,
    db: Database,
    document_type: Annotated[DocumentType, Form()],
    file: Annotated[UploadFile, File()],
) -> Document:
    vendor = db.scalar(select(Vendor).where(Vendor.owner_user_id == current_user.id))
    if vendor is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Create a vendor profile before uploading documents",
        )

    settings = get_settings()
    try:
        stored = await store_validated_upload(file, settings)
    except UploadValidationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    document = Document(
        vendor_id=vendor.id,
        document_type=document_type,
        storage_key=stored.storage_key,
        original_filename=stored.original_filename,
        mime_type=stored.mime_type,
        file_size=stored.file_size,
        processing_status=ProcessingStatus.UPLOADED,
    )
    db.add(document)
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        delete_stored_file(stored.storage_key, settings)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to save document metadata",
        ) from None
    db.refresh(document)
    return document


@router.get("", response_model=list[DocumentResponse])
def list_documents(current_user: VendorUser, db: Database) -> list[Document]:
    return list(
        db.scalars(
            select(Document)
            .join(Vendor, Document.vendor_id == Vendor.id)
            .where(Vendor.owner_user_id == current_user.id)
            .order_by(Document.created_at.desc(), Document.id.desc())
        )
    )


@router.get("/{document_id}", response_model=DocumentResponse)
def read_document(
    document_id: UUID,
    current_user: VendorUser,
    db: Database,
) -> Document:
    return get_owned_document(document_id, current_user, db)


@router.get("/{document_id}/file", response_class=FileResponse)
def download_document(
    document_id: UUID,
    current_user: VendorUser,
    db: Database,
) -> FileResponse:
    document = get_owned_document(document_id, current_user, db)
    try:
        path = resolve_storage_path(document.storage_key, get_settings())
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Document file not found") from exc
    return FileResponse(
        path,
        media_type=document.mime_type,
        filename=document.original_filename,
        content_disposition_type="attachment",
    )
