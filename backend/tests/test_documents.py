from io import BytesIO
from pathlib import Path
import re
from uuid import uuid4

import pymupdf
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.core.config import get_settings
from app.models.documents import Document


@pytest.fixture(autouse=True)
def leave_uploads_unprocessed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def no_op_processing(document_id, db, settings):
        return db.get(Document, document_id)

    monkeypatch.setattr("app.routers.documents.process_document", no_op_processing)


def pdf_bytes() -> bytes:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "Fictional trade license for upload testing")
    content = document.tobytes()
    document.close()
    return content


def image_bytes(image_format: str) -> bytes:
    output = BytesIO()
    Image.new("RGB", (8, 8), color=(20, 120, 180)).save(output, format=image_format)
    return output.getvalue()


def register_profile_and_login(client: TestClient, email: str) -> dict[str, str]:
    password = "correct-horse-battery-staple"
    registration = client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Document Vendor", "password": password},
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
            "address": "1 Fictional Test Road",
        },
    )
    assert profile.status_code == 201
    return headers


def upload(
    client: TestClient,
    headers: dict[str, str],
    filename: str,
    content: bytes,
    mime_type: str,
    document_type: str = "trade_license",
):
    return client.post(
        "/api/v1/documents/upload",
        headers=headers,
        data={"document_type": document_type},
        files={"file": (filename, content, mime_type)},
    )


@pytest.mark.parametrize(
    ("filename", "mime_type", "content"),
    [
        ("license.pdf", "application/pdf", pdf_bytes()),
        ("registration.jpg", "image/jpeg", image_bytes("JPEG")),
        ("registration.jpeg", "image/jpeg", image_bytes("JPEG")),
        ("tax-certificate.png", "image/png", image_bytes("PNG")),
    ],
)
def test_supported_documents_upload_list_read_and_download(
    client: TestClient,
    isolate_document_storage: Path,
    filename: str,
    mime_type: str,
    content: bytes,
) -> None:
    headers = register_profile_and_login(client, f"valid-{filename}@example.com")

    created = upload(client, headers, filename, content, mime_type)

    assert created.status_code == 201
    body = created.json()
    assert body["original_filename"] == filename
    assert body["mime_type"] == mime_type
    assert body["file_size"] == len(content)
    assert body["processing_status"] == "uploaded"
    assert "storage_key" not in body

    listed = client.get("/api/v1/documents", headers=headers)
    detail = client.get(f"/api/v1/documents/{body['id']}", headers=headers)
    downloaded = client.get(f"/api/v1/documents/{body['id']}/file", headers=headers)

    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [body["id"]]
    assert detail.status_code == 200
    assert detail.json() == body
    assert downloaded.status_code == 200
    assert downloaded.content == content
    assert "attachment" in downloaded.headers["content-disposition"]

    stored_files = list(isolate_document_storage.iterdir())
    assert len(stored_files) == 1
    assert stored_files[0].name != filename
    assert re.fullmatch(r"[0-9a-f]{32}\.(pdf|jpg|png)", stored_files[0].name)


def test_unsupported_file_type_is_rejected(
    client: TestClient,
    isolate_document_storage: Path,
) -> None:
    headers = register_profile_and_login(client, "unsupported-file@example.com")

    response = upload(client, headers, "notes.txt", b"plain text", "text/plain")

    assert response.status_code == 415
    assert "PDF, JPG, JPEG, or PNG" in response.json()["detail"]
    assert not isolate_document_storage.exists()


def test_oversized_file_is_rejected_and_removed(
    client: TestClient,
    isolate_document_storage: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers = register_profile_and_login(client, "oversized-file@example.com")
    monkeypatch.setattr(get_settings(), "document_max_file_size_bytes", 1024)

    response = upload(
        client,
        headers,
        "large.pdf",
        pdf_bytes() + (b"x" * 2048),
        "application/pdf",
    )

    assert response.status_code == 413
    assert not list(isolate_document_storage.glob("*"))


@pytest.mark.parametrize(
    ("filename", "mime_type", "content"),
    [
        ("broken.pdf", "application/pdf", b"%PDF-1.7\nnot a real pdf\n%%EOF"),
        ("broken.jpg", "image/jpeg", b"\xff\xd8\xffnot-a-real-image"),
        ("broken.png", "image/png", b"\x89PNG\r\n\x1a\nnot-a-real-image"),
    ],
)
def test_corrupt_files_are_rejected_and_removed(
    client: TestClient,
    isolate_document_storage: Path,
    filename: str,
    mime_type: str,
    content: bytes,
) -> None:
    headers = register_profile_and_login(client, f"corrupt-{filename}@example.com")

    response = upload(client, headers, filename, content, mime_type)

    assert response.status_code == 400
    assert response.json() == {"detail": "File is corrupt or unreadable"}
    assert not list(isolate_document_storage.glob("*"))


def test_empty_file_is_rejected(client: TestClient) -> None:
    headers = register_profile_and_login(client, "empty-file@example.com")

    response = upload(client, headers, "empty.pdf", b"", "application/pdf")

    assert response.status_code == 400
    assert response.json() == {"detail": "File is empty"}


def test_signature_mismatch_is_rejected(client: TestClient) -> None:
    headers = register_profile_and_login(client, "mismatch-file@example.com")

    response = upload(
        client, headers, "pretend.pdf", image_bytes("PNG"), "application/pdf"
    )

    assert response.status_code == 415
    assert response.json() == {"detail": "File signature does not match its type"}


def test_document_endpoints_require_authentication(client: TestClient) -> None:
    unknown_id = uuid4()

    assert client.post(
        "/api/v1/documents/upload",
        data={"document_type": "other"},
        files={"file": ("test.pdf", pdf_bytes(), "application/pdf")},
    ).status_code == 401
    assert client.get("/api/v1/documents").status_code == 401
    assert client.get(f"/api/v1/documents/{unknown_id}").status_code == 401
    assert client.get(f"/api/v1/documents/{unknown_id}/file").status_code == 401


@pytest.mark.parametrize(
    ("filename", "email"),
    [
        ("../escape.pdf", "traversal-forward@example.com"),
        ("..\\escape.pdf", "traversal-backward@example.com"),
    ],
)
def test_path_traversal_filename_is_rejected(
    client: TestClient,
    isolate_document_storage: Path,
    tmp_path: Path,
    filename: str,
    email: str,
) -> None:
    headers = register_profile_and_login(client, email)

    response = upload(client, headers, filename, pdf_bytes(), "application/pdf")

    assert response.status_code == 400
    assert response.json() == {"detail": "Filename must be a plain file name"}
    assert not isolate_document_storage.exists()
    assert not (tmp_path / "escape.pdf").exists()


def test_cross_vendor_document_access_is_hidden(client: TestClient) -> None:
    first_headers = register_profile_and_login(client, "document-owner@example.com")
    second_headers = register_profile_and_login(client, "document-other@example.com")
    created = upload(
        client,
        first_headers,
        "private.pdf",
        pdf_bytes(),
        "application/pdf",
    )
    document_id = created.json()["id"]

    assert client.get("/api/v1/documents", headers=second_headers).json() == []
    metadata = client.get(
        f"/api/v1/documents/{document_id}", headers=second_headers
    )
    file_response = client.get(
        f"/api/v1/documents/{document_id}/file", headers=second_headers
    )

    assert metadata.status_code == 404
    assert file_response.status_code == 404
    assert metadata.json() == file_response.json() == {"detail": "Document not found"}


def test_vendor_profile_is_required_before_upload(client: TestClient) -> None:
    password = "correct-horse-battery-staple"
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "no-profile@example.com",
            "full_name": "No Profile",
            "password": password,
        },
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "no-profile@example.com", "password": password},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = upload(
        client, headers, "license.pdf", pdf_bytes(), "application/pdf"
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Create a vendor profile before uploading documents"
    }
