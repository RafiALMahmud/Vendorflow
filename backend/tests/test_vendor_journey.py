"""Golden-path integration test for the complete Developer 1 vendor journey."""

from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.services.document_access import build_verified_vendor_snapshot
from tests.fixtures.synthetic_documents import synthetic_digital_pdf_bytes


PASSWORD = "correct-horse-battery-staple"


def register_and_login(client: TestClient, email: str) -> dict[str, str]:
    registration = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": "Fictional Journey Vendor",
            "password": PASSWORD,
        },
    )
    assert registration.status_code == 201
    assert registration.json()["role"] == "vendor"

    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_complete_vendor_journey_and_cross_vendor_isolation(
    client: TestClient,
    db_session: Session,
) -> None:
    owner_headers = register_and_login(client, "journey-owner@example.com")

    created_profile = client.post(
        "/api/v1/vendors/me",
        headers=owner_headers,
        json={
            "company_name": "Northstar Fictional Trading Ltd",
            "registration_number": "REG-FIC-2026-001",
            "contact_email": "operations@northstar-fictional.example",
            "phone": "+880 1700-000000",
            "address": "1 Fictional Journey Road, Dhaka",
        },
    )
    assert created_profile.status_code == 201

    edited_profile = client.patch(
        "/api/v1/vendors/me",
        headers=owner_headers,
        json={
            "phone": "+880 1711-111111",
            "address": "2 Updated Fictional Journey Road, Dhaka",
        },
    )
    assert edited_profile.status_code == 200
    assert edited_profile.json()["phone"] == "+880 1711-111111"

    pdf_content = synthetic_digital_pdf_bytes()
    uploaded = client.post(
        "/api/v1/documents/upload",
        headers=owner_headers,
        data={"document_type": "trade_license"},
        files={
            "file": (
                "fictional-journey-trade-license.pdf",
                pdf_content,
                "application/pdf",
            )
        },
    )
    assert uploaded.status_code == 201
    uploaded_body = uploaded.json()
    assert uploaded_body["processing_status"] == "processed"
    document_id = uploaded_body["id"]

    extracted = client.get(
        f"/api/v1/documents/{document_id}/extracted-fields",
        headers=owner_headers,
    )
    assert extracted.status_code == 200
    raw_fields = {field["field_name"]: field for field in extracted.json()}
    assert set(raw_fields) == {
        "company_name",
        "registration_number",
        "license_number",
        "issue_date",
        "expiry_date",
        "tax_identifier",
    }
    assert all(field["review_status"] == "unreviewed" for field in raw_fields.values())
    assert all(field["confirmed_value"] is None for field in raw_fields.values())

    corrected_registration = "REG-FIC-2026-001-CORRECTED"
    reviewed = client.patch(
        f"/api/v1/documents/{document_id}/extracted-fields",
        headers=owner_headers,
        json={
            "fields": [
                {
                    "field_name": "company_name",
                    "confirmed_value": raw_fields["company_name"]["raw_value"],
                    "review_status": "confirmed",
                },
                {
                    "field_name": "registration_number",
                    "confirmed_value": corrected_registration,
                    "review_status": "corrected",
                },
                {
                    "field_name": "expiry_date",
                    "confirmed_value": raw_fields["expiry_date"]["normalized_value"],
                    "review_status": "confirmed",
                },
            ]
        },
    )
    assert reviewed.status_code == 200

    reloaded = client.get(
        f"/api/v1/documents/{document_id}/extracted-fields",
        headers=owner_headers,
    )
    assert reloaded.status_code == 200
    saved_fields = {field["field_name"]: field for field in reloaded.json()}
    assert saved_fields["company_name"]["review_status"] == "confirmed"
    assert saved_fields["registration_number"]["review_status"] == "corrected"
    assert saved_fields["registration_number"]["confirmed_value"] == corrected_registration
    assert (
        saved_fields["registration_number"]["raw_value"]
        == raw_fields["registration_number"]["raw_value"]
    )
    assert saved_fields["tax_identifier"]["review_status"] == "unreviewed"

    downloaded = client.get(
        f"/api/v1/documents/{document_id}/file",
        headers=owner_headers,
    )
    assert downloaded.status_code == 200
    assert downloaded.content == pdf_content

    snapshot = build_verified_vendor_snapshot(
        UUID(created_profile.json()["id"]),
        db_session,
    )
    snapshot_fields = snapshot.documents[0].fields
    assert snapshot.company_name == "Northstar Fictional Trading Ltd"
    assert snapshot_fields["company_name"].verified_value == (
        "Northstar Fictional Trading Ltd"
    )
    assert snapshot_fields["registration_number"].verified_value == (
        corrected_registration
    )
    assert snapshot_fields["tax_identifier"].verified_value is None

    other_headers = register_and_login(client, "journey-other@example.com")
    other_profile = client.post(
        "/api/v1/vendors/me",
        headers=other_headers,
        json={
            "company_name": "Other Fictional Vendor Ltd",
            "registration_number": "OTHER-REG-001",
            "contact_email": "operations@other-fictional.example",
            "phone": "+880 1800-000000",
            "address": "9 Other Fictional Road, Dhaka",
        },
    )
    assert other_profile.status_code == 201
    assert client.get("/api/v1/documents", headers=other_headers).json() == []

    owner_only_paths = (
        f"/api/v1/documents/{document_id}",
        f"/api/v1/documents/{document_id}/file",
        f"/api/v1/documents/{document_id}/extracted-fields",
    )
    for path in owner_only_paths:
        response = client.get(path, headers=other_headers)
        assert response.status_code == 404
        assert response.json() == {"detail": "Document not found"}

    cross_vendor_edit = client.patch(
        f"/api/v1/documents/{document_id}/extracted-fields",
        headers=other_headers,
        json={
            "fields": [
                {
                    "field_name": "company_name",
                    "confirmed_value": "Tampered Vendor",
                    "review_status": "corrected",
                }
            ]
        },
    )
    assert cross_vendor_edit.status_code == 404
    assert cross_vendor_edit.json() == {"detail": "Document not found"}

    owner_after_attempt = client.get(
        f"/api/v1/documents/{document_id}/extracted-fields",
        headers=owner_headers,
    )
    assert owner_after_attempt.status_code == 200
    owner_fields = {
        field["field_name"]: field for field in owner_after_attempt.json()
    }
    assert owner_fields["registration_number"]["confirmed_value"] == (
        corrected_registration
    )
