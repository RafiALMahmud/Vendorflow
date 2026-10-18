"""Release-kit regressions; real OCR is opt-in and never replaced by a mock."""
from datetime import date
import json
import os
from pathlib import Path

import pymupdf
import pytest

from app.schemas.risk import VendorSnapshot
from app.services.extraction import extract_document_text, parse_fictional_document
from app.services.risk_engine import assess_risk

CORPUS = Path(__file__).parent / 'fixtures' / 'vendorflow_qa'
MANIFEST = json.loads((CORPUS / 'expected_results.json').read_text())


@pytest.mark.parametrize('item', MANIFEST['documents'][:3], ids=lambda item: item['file'])
def test_supplied_digital_pdfs_match_every_expected_field(item):
    result = extract_document_text(CORPUS / item['file'], 'application/pdf')
    assert result.method == 'pdf_text'
    fields = {field.field_name: field.normalized_value or field.raw_value
              for field in parse_fictional_document(result.text)}
    assert fields == item['expected']


def test_identifier_prefixes_and_document_headings_are_not_field_labels():
    assert parse_fictional_document('REG-2026-0042\nTIN-TEST-642100\nTRADE LICENSE\nACTIVE SAMPLE') == []


def test_windows_ocr_line_endings_and_inline_columns_preserve_identifiers():
    item = MANIFEST['documents'][3]
    text = '\r\r\n'.join(key.replace('_', ' ').upper() + '  ' + value
                           for key, value in item['expected'].items())
    assert {field.field_name: field.normalized_value or field.raw_value
            for field in parse_fictional_document(text)} == item['expected']


@pytest.mark.real_ocr
@pytest.mark.skipif(os.getenv('RUN_REAL_OCR') != '1', reason='Set RUN_REAL_OCR=1 for installed real Tesseract')
def test_supplied_image_only_pdf_executes_real_ocr():
    item = MANIFEST['documents'][3]
    with pymupdf.open(CORPUS / item['file']) as pdf:
        assert all(not page.get_text().strip() for page in pdf)
    result = extract_document_text(CORPUS / item['file'], 'application/pdf')
    assert result.method == 'tesseract_ocr'
    assert {field.field_name: field.normalized_value or field.raw_value
            for field in parse_fictional_document(result.text)} == item['expected']


def test_negative_fixture_only_asserts_expiry_and_mismatch_after_verification():
    item = MANIFEST['documents'][3]
    data = {'vendor_id': 'fixture-vendor', 'company_name': 'NORTHSTAR TRADING LTD', 'documents': [{
        'document_id': 'fixture-scan', 'document_type': 'trade_license', 'processing_status': 'processed',
        'fields': {name: {'raw_value': value, 'confirmed_value': None, 'review_status': 'unreviewed'}
                   for name, value in item['expected'].items()}}]}
    unverified = assess_risk(VendorSnapshot.model_validate(data), date(2026, 10, 19))
    assert not {'expired_license', 'confirmed_company_name_mismatch'} & {f.code for f in unverified.findings}
    for field in data['documents'][0]['fields'].values():
        field.update(confirmed_value=field['raw_value'], review_status='confirmed')
    verified = assess_risk(VendorSnapshot.model_validate(data), date(2026, 10, 19))
    assert verified.score == 25
    assert {f.code for f in verified.findings} == {
        'missing_required_document', 'expired_license', 'confirmed_company_name_mismatch'}
