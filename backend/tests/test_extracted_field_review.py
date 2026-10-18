from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import create_access_token
from app.models.documents import (
    Document,
    DocumentType,
    ExtractedField,
    ProcessingStatus,
    ReviewStatus,
)
from app.models.identity import User, UserRole, Vendor


@dataclass
class ReviewFixture:
    document: Document
    company: ExtractedField
    expiry: ExtractedField
    headers: dict[str, str]


def create_review_fixture(db: Session, suffix: str) -> ReviewFixture:
    user = User(
        email=f"review-{suffix}@example.com",
        full_name=f"Review Vendor {suffix}",
        password_hash="not-used-by-token-auth",
        role=UserRole.VENDOR,
    )
    vendor = Vendor(
        owner=user,
        company_name=f"Fictional Vendor {suffix}",
        registration_number=f"REG-{suffix}",
        contact_email=f"review-{suffix}@example.com",
        phone="+880 1700-000000",
        address="1 Fictional Review Road",
    )
    document = Document(
        vendor=vendor,
        document_type=DocumentType.TRADE_LICENSE,
        storage_key=f"review-{suffix}.pdf",
        original_filename=f"review-{suffix}.pdf",
        mime_type="application/pdf",
        file_size=100,
        processing_status=ProcessingStatus.PROCESSED,
    )
    company = ExtractedField(
        document=document,
        field_name="company_name",
        raw_value="Fictional OCR Company Ltd",
        normalized_value=None,
        confirmed_value=None,
        review_status=ReviewStatus.UNREVIEWED,
        extraction_method="pdf_text",
    )
    expiry = ExtractedField(
        document=document,
        field_name="expiry_date",
        raw_value="17 October 2027",
        normalized_value="2027-10-17",
        confirmed_value=None,
        review_status=ReviewStatus.UNREVIEWED,
        extraction_method="pdf_text",
    )
    db.add_all([company, expiry])
    db.commit()
    token, _ = create_access_token(user.id)
    return ReviewFixture(
        document=document,
        company=company,
        expiry=expiry,
        headers={"Authorization": f"Bearer {token}"},
    )


def patch_field(
    client: TestClient,
    fixture: ReviewFixture,
    *,
    field_name: str,
    confirmed_value: str,
    review_status: str,
):
    return client.patch(
        f"/api/v1/documents/{fixture.document.id}/extracted-fields",
        headers=fixture.headers,
        json={
            "fields": [
                {
                    "field_name": field_name,
                    "confirmed_value": confirmed_value,
                    "review_status": review_status,
                }
            ]
        },
    )


def test_vendor_confirms_extracted_candidate(
    client: TestClient, db_session: Session
) -> None:
    fixture = create_review_fixture(db_session, "confirm")

    response = patch_field(
        client,
        fixture,
        field_name="expiry_date",
        confirmed_value="2027-10-17",
        review_status="confirmed",
    )

    assert response.status_code == 200
    saved = db_session.get(ExtractedField, fixture.expiry.id)
    assert saved is not None
    assert saved.confirmed_value == "2027-10-17"
    assert saved.review_status == ReviewStatus.CONFIRMED
    assert saved.raw_value == "17 October 2027"
    assert saved.normalized_value == "2027-10-17"


def test_vendor_corrects_value_without_changing_raw_data(
    client: TestClient, db_session: Session
) -> None:
    fixture = create_review_fixture(db_session, "correct")

    response = patch_field(
        client,
        fixture,
        field_name="company_name",
        confirmed_value="Fictional Correct Company Ltd",
        review_status="corrected",
    )

    assert response.status_code == 200
    db_session.expire_all()
    saved = db_session.get(ExtractedField, fixture.company.id)
    assert saved is not None
    assert saved.raw_value == "Fictional OCR Company Ltd"
    assert saved.normalized_value is None
    assert saved.confirmed_value == "Fictional Correct Company Ltd"
    assert saved.review_status == ReviewStatus.CORRECTED


def test_saved_review_states_are_returned_by_a_fresh_get(
    client: TestClient, db_session: Session
) -> None:
    fixture = create_review_fixture(db_session, "reload")
    response = client.patch(
        f"/api/v1/documents/{fixture.document.id}/extracted-fields",
        headers=fixture.headers,
        json={
            "fields": [
                {
                    "field_name": "company_name",
                    "confirmed_value": "Fictional OCR Company Ltd",
                    "review_status": "confirmed",
                },
                {
                    "field_name": "expiry_date",
                    "confirmed_value": "2028-01-31",
                    "review_status": "corrected",
                },
            ]
        },
    )
    assert response.status_code == 200

    reloaded = client.get(
        f"/api/v1/documents/{fixture.document.id}/extracted-fields",
        headers=fixture.headers,
    )

    assert reloaded.status_code == 200
    by_name = {field["field_name"]: field for field in reloaded.json()}
    assert by_name["company_name"]["review_status"] == "confirmed"
    assert by_name["company_name"]["confirmed_value"] == (
        "Fictional OCR Company Ltd"
    )
    assert by_name["expiry_date"]["review_status"] == "corrected"
    assert by_name["expiry_date"]["confirmed_value"] == "2028-01-31"
    assert by_name["expiry_date"]["raw_value"] == "17 October 2027"


@pytest.mark.parametrize(
    ("payload", "detail_fragment"),
    [
        (
            {
                "fields": [
                    {
                        "field_name": "unexpected_field",
                        "confirmed_value": "value",
                        "review_status": "corrected",
                    }
                ]
            },
            "Input should be",
        ),
        (
            {
                "fields": [
                    {
                        "field_name": "tax_identifier",
                        "confirmed_value": "TAX-NEW",
                        "review_status": "corrected",
                    }
                ]
            },
            "was not extracted for this document",
        ),
        (
            {
                "fields": [
                    {
                        "field_name": "company_name",
                        "confirmed_value": "Changed",
                        "review_status": "confirmed",
                    }
                ]
            },
            "must match the extracted candidate",
        ),
        (
            {
                "fields": [
                    {
                        "field_name": "company_name",
                        "confirmed_value": "Fictional OCR Company Ltd",
                        "review_status": "corrected",
                    }
                ]
            },
            "must differ from the extracted candidate",
        ),
        (
            {
                "fields": [
                    {
                        "field_name": "expiry_date",
                        "confirmed_value": "31/01/2028",
                        "review_status": "corrected",
                    }
                ]
            },
            "YYYY-MM-DD",
        ),
        (
            {
                "fields": [
                    {
                        "field_name": "company_name",
                        "confirmed_value": "Fictional OCR Company Ltd",
                        "review_status": "confirmed",
                        "unexpected": True,
                    }
                ]
            },
            "Extra inputs are not permitted",
        ),
    ],
)
def test_invalid_field_updates_are_rejected(
    client: TestClient,
    db_session: Session,
    payload: dict,
    detail_fragment: str,
) -> None:
    fixture = create_review_fixture(db_session, detail_fragment[:8].replace(" ", "-"))

    response = client.patch(
        f"/api/v1/documents/{fixture.document.id}/extracted-fields",
        headers=fixture.headers,
        json=payload,
    )

    assert response.status_code == 422
    assert detail_fragment in str(response.json()["detail"])
    db_session.refresh(fixture.company)
    assert fixture.company.raw_value == "Fictional OCR Company Ltd"
    assert fixture.company.confirmed_value is None
    assert fixture.company.review_status == ReviewStatus.UNREVIEWED


def test_duplicate_updates_and_malformed_payload_are_rejected(
    client: TestClient, db_session: Session
) -> None:
    fixture = create_review_fixture(db_session, "malformed")
    duplicate = {
        "fields": [
            {
                "field_name": "company_name",
                "confirmed_value": "Fictional OCR Company Ltd",
                "review_status": "confirmed",
            },
            {
                "field_name": "company_name",
                "confirmed_value": "Correction",
                "review_status": "corrected",
            },
        ]
    }

    assert client.patch(
        f"/api/v1/documents/{fixture.document.id}/extracted-fields",
        headers=fixture.headers,
        json=duplicate,
    ).status_code == 422
    assert client.patch(
        f"/api/v1/documents/{fixture.document.id}/extracted-fields",
        headers=fixture.headers,
        json={"fields": []},
    ).status_code == 422
    assert client.patch(
        f"/api/v1/documents/{fixture.document.id}/extracted-fields",
        headers=fixture.headers,
        json={"wrong": []},
    ).status_code == 422


def test_cross_vendor_and_unauthenticated_review_access_is_hidden(
    client: TestClient, db_session: Session
) -> None:
    owner = create_review_fixture(db_session, "owner")
    other = create_review_fixture(db_session, "other")
    path = f"/api/v1/documents/{owner.document.id}/extracted-fields"
    payload = {
        "fields": [
            {
                "field_name": "company_name",
                "confirmed_value": "Fictional OCR Company Ltd",
                "review_status": "confirmed",
            }
        ]
    }

    assert client.get(path, headers=other.headers).status_code == 404
    assert client.patch(path, headers=other.headers, json=payload).status_code == 404
    assert client.patch(path, json=payload).status_code == 401

    stored = db_session.scalar(
        select(ExtractedField).where(ExtractedField.id == owner.company.id)
    )
    assert stored is not None
    assert stored.review_status == ReviewStatus.UNREVIEWED
    assert stored.confirmed_value is None
