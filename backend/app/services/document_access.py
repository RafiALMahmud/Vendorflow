"""Stable, vendor-scoped document snapshots for review-side consumers."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.contracts.verified_data import (
    VerifiedDocumentSnapshot,
    VerifiedFieldSnapshot,
    VerifiedVendorSnapshot,
)
from app.models.documents import Document, ExtractedField
from app.models.identity import Vendor


class VendorSnapshotNotFoundError(LookupError):
    """Raised when a snapshot is requested for a vendor that does not exist."""


def build_verified_vendor_snapshot(
    vendor_id: UUID,
    db: Session,
) -> VerifiedVendorSnapshot:
    """Build the deterministic document handoff for exactly one vendor.

    Raw OCR values remain visible as evidence, but consumers must use
    ``VerifiedFieldSnapshot.verified_value``. That property returns data only
    after the vendor has explicitly confirmed or corrected the field.
    """

    vendor = db.scalar(select(Vendor).where(Vendor.id == vendor_id))
    if vendor is None:
        raise VendorSnapshotNotFoundError(f"Vendor {vendor_id} was not found")

    documents = list(
        db.scalars(
            select(Document)
            .where(Document.vendor_id == vendor.id)
            .order_by(Document.created_at.asc(), Document.id.asc())
        )
    )
    fields_by_document: dict[UUID, list[ExtractedField]] = {
        document.id: [] for document in documents
    }
    if documents:
        document_ids = [document.id for document in documents]
        extracted_fields = db.scalars(
            select(ExtractedField)
            .where(ExtractedField.document_id.in_(document_ids))
            .order_by(
                ExtractedField.document_id.asc(),
                ExtractedField.field_name.asc(),
                ExtractedField.id.asc(),
            )
        )
        for field in extracted_fields:
            fields_by_document[field.document_id].append(field)

    document_snapshots: list[VerifiedDocumentSnapshot] = []

    for document in documents:
        fields = {
            field.field_name: VerifiedFieldSnapshot(
                raw_value=field.raw_value,
                confirmed_value=field.confirmed_value,
                review_status=field.review_status.value,
            )
            for field in fields_by_document[document.id]
        }
        document_snapshots.append(
            VerifiedDocumentSnapshot(
                document_id=document.id,
                document_type=document.document_type.value,
                processing_status=document.processing_status.value,
                fields=fields,
            )
        )

    return VerifiedVendorSnapshot(
        vendor_id=vendor.id,
        company_name=vendor.company_name,
        documents=tuple(document_snapshots),
    )
