from pathlib import Path
import logging

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.documents import (
    Document,
    DocumentType,
    ExtractedField,
    ProcessingStatus,
    ReviewStatus,
)
from app.models.identity import User, UserRole, Vendor
from app.services import extraction
from app.services.extraction import (
    OCR_METHOD,
    PDF_TEXT_METHOD,
    ExtractionFailure,
    TesseractUnavailable,
    extract_document_text,
    normalize_date,
    parse_fictional_document,
    process_document,
)
from tests.fixtures.synthetic_documents import (
    FICTIONAL_DOCUMENT_TEXT,
    synthetic_digital_pdf_bytes,
    synthetic_scanned_image_bytes,
    synthetic_scanned_pdf_bytes,
)


def stored_document(
    db_session: Session,
    storage_dir: Path,
    *,
    filename: str,
    content: bytes,
    mime_type: str,
) -> Document:
    user = User(
        email=f"{filename}@example.com",
        full_name="Extraction Fixture",
        password_hash="not-used",
        role=UserRole.VENDOR,
    )
    vendor = Vendor(
        owner=user,
        company_name="Northstar Fictional Trading Ltd",
        registration_number="REG-FIC-2026-001",
        contact_email=f"{filename}@example.com",
        phone="+880 1700-000000",
        address="1 Synthetic Fixture Road",
    )
    storage_dir.mkdir(parents=True, exist_ok=True)
    storage_key = filename
    (storage_dir / storage_key).write_bytes(content)
    document = Document(
        vendor=vendor,
        document_type=DocumentType.TRADE_LICENSE,
        storage_key=storage_key,
        original_filename=filename,
        mime_type=mime_type,
        file_size=len(content),
        processing_status=ProcessingStatus.UPLOADED,
    )
    db_session.add(document)
    db_session.commit()
    return document


def test_digital_pdf_uses_selectable_text_before_ocr(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "fictional-digital.pdf"
    path.write_bytes(synthetic_digital_pdf_bytes())

    def unexpected_ocr(*args, **kwargs):
        raise AssertionError("OCR must not run when selectable PDF text exists")

    monkeypatch.setattr(extraction, "_run_tesseract", unexpected_ocr)

    result = extract_document_text(path, "application/pdf")

    assert result.method == PDF_TEXT_METHOD
    assert "Northstar Fictional Trading Ltd" in result.text
    assert "REG-FIC-2026-001" in result.text


def test_scanned_image_uses_mocked_tesseract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "fictional-scan.png"
    path.write_bytes(synthetic_scanned_image_bytes())
    observed: dict[str, bytes] = {}

    def mock_ocr(image_bytes: bytes, settings) -> str:
        observed["image"] = image_bytes
        return FICTIONAL_DOCUMENT_TEXT

    monkeypatch.setattr(extraction, "_run_tesseract", mock_ocr)

    result = extract_document_text(path, "image/png")

    assert result.method == OCR_METHOD
    assert result.text == FICTIONAL_DOCUMENT_TEXT
    assert observed["image"].startswith(b"\x89PNG\r\n\x1a\n")


def test_image_only_pdf_falls_back_to_mocked_ocr(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "fictional-scanned.pdf"
    path.write_bytes(synthetic_scanned_pdf_bytes())
    calls = 0

    def mock_ocr(image_bytes: bytes, settings) -> str:
        nonlocal calls
        calls += 1
        assert image_bytes.startswith(b"\x89PNG\r\n\x1a\n")
        return FICTIONAL_DOCUMENT_TEXT

    monkeypatch.setattr(extraction, "_run_tesseract", mock_ocr)

    result = extract_document_text(path, "application/pdf")

    assert result.method == OCR_METHOD
    assert calls == 1
    assert result.text == FICTIONAL_DOCUMENT_TEXT


def test_parser_extracts_only_labeled_fields_and_normalizes_clear_dates() -> None:
    parsed = {field.field_name: field for field in parse_fictional_document(
        FICTIONAL_DOCUMENT_TEXT + "\nUnrelated Note: Do not parse me"
    )}

    assert set(parsed) == {
        "company_name",
        "registration_number",
        "license_number",
        "issue_date",
        "expiry_date",
        "tax_identifier",
    }
    assert parsed["company_name"].raw_value == "Northstar Fictional Trading Ltd"
    assert parsed["issue_date"].raw_value == "17 October 2026"
    assert parsed["issue_date"].normalized_value == "2026-10-17"
    assert parsed["expiry_date"].normalized_value == "2027-10-16"
    assert all(parsed[name].review_note is None for name in parsed)


def test_ambiguous_and_invalid_dates_are_flagged_for_human_review() -> None:
    ambiguous, ambiguous_note = normalize_date("04/05/2026")
    invalid, invalid_note = normalize_date("2026-19-45")

    assert ambiguous is None
    assert ambiguous_note == "Ambiguous numeric date; confirm the day/month order."
    assert invalid is None
    assert invalid_note == "Date could not be normalized; review the original value manually."


def test_missing_tesseract_is_reported_without_claiming_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "requires-ocr.png"
    path.write_bytes(synthetic_scanned_image_bytes())
    settings = get_settings()
    monkeypatch.setattr(settings, "tesseract_cmd", None)
    monkeypatch.setattr(extraction.shutil, "which", lambda command: None)

    with pytest.raises(TesseractUnavailable, match="not installed"):
        extract_document_text(path, "image/png", settings)


def test_processing_persists_unverified_fields_and_iso_candidates(
    db_session: Session,
    isolate_document_storage: Path,
) -> None:
    document = stored_document(
        db_session,
        isolate_document_storage,
        filename="fixture-digital.pdf",
        content=synthetic_digital_pdf_bytes(),
        mime_type="application/pdf",
    )

    processed = process_document(document.id, db_session)
    fields = list(
        db_session.scalars(
            select(ExtractedField).where(ExtractedField.document_id == document.id)
        )
    )

    assert processed.processing_status is ProcessingStatus.PROCESSED
    assert processed.processing_error is None
    assert len(fields) == 6
    assert all(field.review_status is ReviewStatus.UNREVIEWED for field in fields)
    assert all(field.confirmed_value is None for field in fields)
    assert all(field.extraction_method == PDF_TEXT_METHOD for field in fields)
    expiry = next(field for field in fields if field.field_name == "expiry_date")
    assert expiry.raw_value == "2027-10-16"
    assert expiry.normalized_value == "2027-10-16"


def test_processing_failure_sets_failed_status_and_retry_guidance(
    db_session: Session,
    isolate_document_storage: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document = stored_document(
        db_session,
        isolate_document_storage,
        filename="fixture-scan.png",
        content=synthetic_scanned_image_bytes(),
        mime_type="image/png",
    )

    def unavailable(*args, **kwargs):
        raise TesseractUnavailable(
            "Tesseract OCR is unavailable. Install it and re-upload this document."
        )

    monkeypatch.setattr(extraction, "extract_document_text", unavailable)

    processed = process_document(document.id, db_session)

    assert processed.processing_status is ProcessingStatus.FAILED
    assert processed.processing_error is not None
    assert "Install it and re-upload" in processed.processing_error
    assert db_session.scalar(
        select(ExtractedField).where(ExtractedField.document_id == document.id)
    ) is None


def test_unexpected_extraction_error_is_sanitized_in_database_and_logs(
    db_session: Session,
    isolate_document_storage: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    document = stored_document(
        db_session,
        isolate_document_storage,
        filename="sensitive-failure.pdf",
        content=synthetic_digital_pdf_bytes(),
        mime_type="application/pdf",
    )
    sensitive_detail = "SECRET-DOCUMENT-CONTENT C:\\private\\upload.pdf"

    def unexpected_failure(*args, **kwargs):
        raise RuntimeError(sensitive_detail)

    monkeypatch.setattr(extraction, "parse_fictional_document", unexpected_failure)
    with caplog.at_level(logging.ERROR, logger="app.services.extraction"):
        processed = process_document(document.id, db_session)

    assert processed.processing_status is ProcessingStatus.FAILED
    assert processed.processing_error == (
        "Document processing failed safely. Re-upload the document or contact support."
    )
    assert sensitive_detail not in processed.processing_error
    assert sensitive_detail not in caplog.text
    assert str(isolate_document_storage) not in caplog.text


def test_unreadable_document_reports_safe_failure(tmp_path: Path) -> None:
    path = tmp_path / "corrupt.pdf"
    path.write_bytes(b"%PDF-1.7\nnot-readable\n%%EOF")

    with pytest.raises(ExtractionFailure, match="unreadable"):
        extract_document_text(path, "application/pdf")


def test_upload_processes_digital_pdf_and_extracted_fields_are_owner_scoped(
    client: TestClient,
) -> None:
    owner_headers = _register_profile_login(client, "extraction-owner@example.com")
    other_headers = _register_profile_login(client, "extraction-other@example.com")
    upload = client.post(
        "/api/v1/documents/upload",
        headers=owner_headers,
        data={"document_type": "trade_license"},
        files={
            "file": (
                "fictional-digital.pdf",
                synthetic_digital_pdf_bytes(),
                "application/pdf",
            )
        },
    )

    assert upload.status_code == 201
    assert upload.json()["processing_status"] == "processed"
    document_id = upload.json()["id"]
    owner_fields = client.get(
        f"/api/v1/documents/{document_id}/extracted-fields", headers=owner_headers
    )
    other_fields = client.get(
        f"/api/v1/documents/{document_id}/extracted-fields", headers=other_headers
    )

    assert owner_fields.status_code == 200
    assert len(owner_fields.json()) == 6
    assert all(field["review_status"] == "unreviewed" for field in owner_fields.json())
    assert all(field["confirmed_value"] is None for field in owner_fields.json())
    assert other_fields.status_code == 404


def _register_profile_login(client: TestClient, email: str) -> dict[str, str]:
    password = "correct-horse-battery-staple"
    registration = client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Extraction API Fixture", "password": password},
    )
    assert registration.status_code == 201
    login = client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    profile = client.post(
        "/api/v1/vendors/me",
        headers=headers,
        json={
            "company_name": f"{email} Company",
            "registration_number": email,
            "contact_email": email,
            "phone": "+880 1700-000000",
            "address": "1 Synthetic Test Road",
        },
    )
    assert profile.status_code == 201
    return headers
