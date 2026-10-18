from uuid import UUID, uuid4

from app.models.documents import Document, ProcessingStatus
from tests.test_admin import actors, draft, headers, submitted  # noqa: F401
from tests.fixtures.synthetic_documents import synthetic_digital_pdf_bytes


def test_admin_download_is_scoped_to_submission_evidence(client, actors):
    owner, other, admin = actors
    content = synthetic_digital_pdf_bytes()
    upload = client.post('/api/v1/documents/upload', headers=headers(owner), data={'document_type': 'trade_license'},
                         files={'file': ('fictional.pdf', content, 'application/pdf')})
    assert upload.status_code == 201
    doc_id = upload.json()['id']
    application = submitted(client, owner)
    path = f"/api/v1/admin/applications/{application['id']}/documents/{doc_id}/file"
    response = client.get(path, headers=headers(admin))
    assert response.status_code == 200 and response.content == content
    assert response.headers['cache-control'] == 'private, no-store'
    assert client.get(path).status_code == 401
    assert client.get(path, headers=headers(other)).status_code == 403
    wrong_case = submitted(client, other)
    assert client.get(f"/api/v1/admin/applications/{wrong_case['id']}/documents/{doc_id}/file", headers=headers(admin)).status_code == 404
    assert client.get(f"/api/v1/admin/applications/{application['id']}/documents/{uuid4()}/file", headers=headers(admin)).status_code == 404


def test_retry_is_owner_only_and_preserves_successfully_reviewed_documents(client, db_session, actors):
    owner, other, _ = actors
    uploaded = client.post('/api/v1/documents/upload', headers=headers(owner), data={'document_type': 'trade_license'},
        files={'file': ('fictional.pdf', synthetic_digital_pdf_bytes(), 'application/pdf')}).json()
    path = f"/api/v1/documents/{uploaded['id']}/retry"
    assert client.post(path, headers=headers(owner)).status_code == 409
    assert client.post(path, headers=headers(other)).status_code == 404
    document = db_session.get(Document, UUID(uploaded['id']))
    document.processing_status = ProcessingStatus.FAILED
    document.processing_error = 'Fictional transient failure'
    db_session.commit()
    retried = client.post(path, headers=headers(owner))
    assert retried.status_code == 200 and retried.json()['processing_status'] == 'processed'
    assert retried.json()['processing_error'] is None


def test_tax_certificate_number_can_be_confirmed_and_survives_reload(client, actors):
    from pathlib import Path
    owner, _, _ = actors
    content = (Path(__file__).parent / 'fixtures/vendorflow_qa/03_valid_tax_certificate.pdf').read_bytes()
    document = client.post('/api/v1/documents/upload', headers=headers(owner), data={'document_type': 'tax_certificate'},
        files={'file': ('fictional-tax.pdf', content, 'application/pdf')}).json()
    path = f"/api/v1/documents/{document['id']}/extracted-fields"
    response = client.patch(path, headers=headers(owner), json={'fields': [{
        'field_name': 'certificate_number', 'confirmed_value': 'TAX-2026-6402', 'review_status': 'confirmed'}]})
    assert response.status_code == 200
    field = next(row for row in client.get(path, headers=headers(owner)).json() if row['field_name'] == 'certificate_number')
    assert field['raw_value'] == field['confirmed_value'] == 'TAX-2026-6402'
