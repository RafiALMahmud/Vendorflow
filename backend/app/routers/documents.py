from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.core.auth import require_vendor
from app.core.config import get_settings
from app.db.session import get_db
from app.models.documents import (
    Document,
    DocumentType,
    ExtractedField,
    ProcessingStatus,
    ReviewStatus,
)
from app.models.identity import User, Vendor
from app.schemas.document import (
    DocumentResponse,
    ExtractedFieldResponse,
    ExtractedFieldsReviewRequest,
)
from app.services.document_storage import (
    UploadValidationError,
    delete_stored_file,
    resolve_storage_path,
    store_validated_upload,
)
from app.services.extraction import extracted_fields_for_document, process_document

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
    document = await run_in_threadpool(process_document, document.id, db, settings)
    return document


@router.post('/{document_id}/retry', response_model=DocumentResponse)
def retry_failed_document(document_id: UUID, current_user: VendorUser, db: Database):
    document = db.scalar(owned_document_query(document_id, current_user).with_for_update())
    if document is None:
        raise HTTPException(404, 'Document not found')
    if document.processing_status != ProcessingStatus.FAILED:
        raise HTTPException(409, 'Only failed extraction can be retried; reviewed fields are preserved')
    return process_document(document.id, db, get_settings())


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


@router.get(
    "/{document_id}/extracted-fields",
    response_model=list[ExtractedFieldResponse],
)
def read_extracted_fields(
    document_id: UUID,
    current_user: VendorUser,
    db: Database,
) -> list[ExtractedField]:
    document = get_owned_document(document_id, current_user, db)
    return extracted_fields_for_document(document.id, db)


@router.patch(
    "/{document_id}/extracted-fields",
    response_model=list[ExtractedFieldResponse],
)
def review_extracted_fields(
    document_id: UUID,
    payload: ExtractedFieldsReviewRequest,
    current_user: VendorUser,
    db: Database,
) -> list[ExtractedField]:
    document = get_owned_document(document_id, current_user, db)
    extracted_fields = extracted_fields_for_document(document.id, db)
    fields_by_name = {field.field_name: field for field in extracted_fields}
    validated_updates: list[tuple[ExtractedField, str, ReviewStatus]] = []

    # Validate the complete batch before changing ORM state so malformed requests
    # cannot partially review a document.
    for update in payload.fields:
        field = fields_by_name.get(update.field_name)
        if field is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Field '{update.field_name}' was not extracted for this document",
            )

        candidate_value = field.normalized_value or field.raw_value
        if update.review_status == "confirmed":
            if candidate_value is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=(
                        f"Field '{update.field_name}' has no extracted value to confirm; "
                        "submit a correction instead"
                    ),
                )
            if update.confirmed_value != candidate_value.strip():
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=(
                        f"Confirmed value for '{update.field_name}' must match the "
                        "extracted candidate; use corrected for a changed value"
                    ),
                )
            review_status = ReviewStatus.CONFIRMED
        else:
            if (
                candidate_value is not None
                and update.confirmed_value == candidate_value.strip()
            ):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=(
                        f"Corrected value for '{update.field_name}' must differ from the "
                        "extracted candidate; use confirmed when it is correct"
                    ),
                )
            review_status = ReviewStatus.CORRECTED

        validated_updates.append((field, update.confirmed_value, review_status))

    for field, confirmed_value, review_status in validated_updates:
        field.confirmed_value = confirmed_value
        field.review_status = review_status

    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to save extracted field reviews",
        ) from None

    return extracted_fields_for_document(document.id, db)


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
        headers={'Cache-Control': 'private, no-store', 'X-Content-Type-Options': 'nosniff'},
    )
