from datetime import datetime, timezone
from uuid import UUID

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.contracts.verified_data import ReviewStatus as ContractReviewStatus
from app.contracts.verified_data import VerifiedFieldSnapshot
from app.models.documents import (
    Document,
    DocumentType,
    ExtractedField,
    ProcessingStatus,
    ReviewStatus,
)
from app.models.identity import User, UserRole, Vendor
from app.services.document_access import (
    VendorSnapshotNotFoundError,
    build_verified_vendor_snapshot,
)


def fixed_uuid(value: int) -> UUID:
    return UUID(int=value)


def add_vendor(db: Session, number: int) -> Vendor:
    user = User(
        id=fixed_uuid(number),
        email=f"snapshot-{number}@example.com",
        full_name=f"Snapshot Vendor {number}",
        password_hash="not-used",
        role=UserRole.VENDOR,
    )
    vendor = Vendor(
        id=fixed_uuid(number + 100),
        owner=user,
        company_name=f"Fictional Snapshot Company {number}",
        registration_number=f"REG-{number}",
        contact_email=f"snapshot-{number}@example.com",
        phone="+880 1700-000000",
        address="1 Fictional Contract Road",
    )
    db.add(vendor)
    db.flush()
    return vendor


def add_document(
    db: Session,
    vendor: Vendor,
    number: int,
    *,
    document_type: DocumentType = DocumentType.TRADE_LICENSE,
    processing_status: ProcessingStatus = ProcessingStatus.PROCESSED,
    created_at: datetime | None = None,
) -> Document:
    document = Document(
        id=fixed_uuid(number + 200),
        vendor_id=vendor.id,
        document_type=document_type,
        storage_key=f"snapshot-{number}.pdf",
        original_filename=f"snapshot-{number}.pdf",
        mime_type="application/pdf",
        file_size=100,
        processing_status=processing_status,
        created_at=created_at,
        updated_at=created_at,
    )
    db.add(document)
    db.flush()
    return document


def add_field(
    db: Session,
    document: Document,
    number: int,
    *,
    field_name: str,
    raw_value: str | None,
    confirmed_value: str | None,
    review_status: ReviewStatus,
) -> ExtractedField:
    field = ExtractedField(
        id=fixed_uuid(number + 300),
        document_id=document.id,
        field_name=field_name,
        raw_value=raw_value,
        confirmed_value=confirmed_value,
        review_status=review_status,
        extraction_method="pdf_text",
    )
    db.add(field)
    db.flush()
    return field


def test_snapshot_for_vendor_with_no_documents(db_session: Session) -> None:
    vendor = add_vendor(db_session, 1)
    db_session.commit()

    snapshot = build_verified_vendor_snapshot(vendor.id, db_session)

    assert snapshot.vendor_id == vendor.id
    assert snapshot.company_name == "Fictional Snapshot Company 1"
    assert snapshot.documents == ()
    assert snapshot.model_dump(mode="json") == {
        "vendor_id": str(vendor.id),
        "company_name": "Fictional Snapshot Company 1",
        "documents": [],
    }


def test_unreviewed_field_is_retained_but_never_verified(db_session: Session) -> None:
    vendor = add_vendor(db_session, 2)
    document = add_document(db_session, vendor, 2)
    add_field(
        db_session,
        document,
        2,
        field_name="tax_identifier",
        raw_value="OCR-GUESS-123",
        confirmed_value=None,
        review_status=ReviewStatus.UNREVIEWED,
    )
    db_session.commit()

    field = build_verified_vendor_snapshot(vendor.id, db_session).documents[0].fields[
        "tax_identifier"
    ]

    assert field.raw_value == "OCR-GUESS-123"
    assert field.confirmed_value is None
    assert field.review_status == ContractReviewStatus.UNREVIEWED
    assert field.verified_value is None


def test_corrected_field_exposes_only_vendor_confirmed_value(
    db_session: Session,
) -> None:
    vendor = add_vendor(db_session, 3)
    document = add_document(db_session, vendor, 3)
    add_field(
        db_session,
        document,
        3,
        field_name="registration_number",
        raw_value="OCR-REG-00I",
        confirmed_value="REG-001",
        review_status=ReviewStatus.CORRECTED,
    )
    db_session.commit()

    field = build_verified_vendor_snapshot(vendor.id, db_session).documents[0].fields[
        "registration_number"
    ]

    assert field.raw_value == "OCR-REG-00I"
    assert field.confirmed_value == "REG-001"
    assert field.review_status == ContractReviewStatus.CORRECTED
    assert field.verified_value == "REG-001"


def test_multiple_documents_and_fields_serialize_deterministically(
    db_session: Session,
) -> None:
    vendor = add_vendor(db_session, 4)
    later = datetime(2026, 10, 18, tzinfo=timezone.utc)
    earlier = datetime(2026, 10, 17, tzinfo=timezone.utc)
    second_document = add_document(
        db_session,
        vendor,
        5,
        document_type=DocumentType.TAX_CERTIFICATE,
        created_at=later,
    )
    first_document = add_document(
        db_session,
        vendor,
        4,
        document_type=DocumentType.BUSINESS_REGISTRATION,
        created_at=earlier,
    )
    add_field(
        db_session,
        first_document,
        5,
        field_name="registration_number",
        raw_value="REG-004",
        confirmed_value="REG-004",
        review_status=ReviewStatus.CONFIRMED,
    )
    add_field(
        db_session,
        first_document,
        4,
        field_name="company_name",
        raw_value="Fictional Snapshot Company 4",
        confirmed_value="Fictional Snapshot Company 4",
        review_status=ReviewStatus.CONFIRMED,
    )
    add_field(
        db_session,
        second_document,
        6,
        field_name="tax_identifier",
        raw_value="TAX-004",
        confirmed_value="TAX-004",
        review_status=ReviewStatus.CONFIRMED,
    )
    db_session.commit()

    first = build_verified_vendor_snapshot(vendor.id, db_session)
    second = build_verified_vendor_snapshot(vendor.id, db_session)

    assert [item.document_id for item in first.documents] == [
        first_document.id,
        second_document.id,
    ]
    assert list(first.documents[0].fields) == [
        "company_name",
        "registration_number",
    ]
    assert first.model_dump_json() == second.model_dump_json()


def test_failed_document_is_retained_with_empty_fields(db_session: Session) -> None:
    vendor = add_vendor(db_session, 6)
    document = add_document(
        db_session,
        vendor,
        6,
        processing_status=ProcessingStatus.FAILED,
    )
    db_session.commit()

    snapshot = build_verified_vendor_snapshot(vendor.id, db_session)

    assert len(snapshot.documents) == 1
    assert snapshot.documents[0].document_id == document.id
    assert snapshot.documents[0].processing_status == "failed"
    assert snapshot.documents[0].fields == {}


def test_another_vendors_documents_are_excluded(db_session: Session) -> None:
    requested_vendor = add_vendor(db_session, 7)
    requested_document = add_document(db_session, requested_vendor, 7)
    other_vendor = add_vendor(db_session, 8)
    other_document = add_document(db_session, other_vendor, 8)
    add_field(
        db_session,
        other_document,
        8,
        field_name="tax_identifier",
        raw_value="OTHER-TAX-ID",
        confirmed_value="OTHER-TAX-ID",
        review_status=ReviewStatus.CONFIRMED,
    )
    db_session.commit()

    snapshot = build_verified_vendor_snapshot(requested_vendor.id, db_session)

    assert [item.document_id for item in snapshot.documents] == [
        requested_document.id
    ]
    assert all("tax_identifier" not in item.fields for item in snapshot.documents)


def test_missing_vendor_has_explicit_failure(db_session: Session) -> None:
    missing_vendor_id = fixed_uuid(9999)

    with pytest.raises(VendorSnapshotNotFoundError, match=str(missing_vendor_id)):
        build_verified_vendor_snapshot(missing_vendor_id, db_session)


def test_reviewed_contract_field_requires_a_confirmed_value() -> None:
    with pytest.raises(ValidationError, match="confirmed_value is required"):
        VerifiedFieldSnapshot(
            raw_value="OCR candidate",
            confirmed_value=None,
            review_status=ContractReviewStatus.CONFIRMED,
        )


def test_unreviewed_contract_field_rejects_a_confirmed_value() -> None:
    with pytest.raises(ValidationError, match="must be null"):
        VerifiedFieldSnapshot(
            raw_value="OCR candidate",
            confirmed_value="must-not-be-trusted",
            review_status=ContractReviewStatus.UNREVIEWED,
        )
