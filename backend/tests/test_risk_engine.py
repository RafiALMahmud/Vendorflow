from copy import deepcopy
from datetime import date

import pytest

from app.schemas.risk import RiskRules, VendorSnapshot
from app.services.risk_engine import assess_risk, priority_for_score

TODAY = date(2026, 10, 18)


def field(value, status='confirmed'):
    return {'raw_value': value, 'confirmed_value': value, 'review_status': status}


@pytest.fixture
def snapshot():
    return {'vendor_id': 'fictional-vendor', 'company_name': 'Sample Trading Ltd',
            'documents': [
                {'document_id': kind, 'document_type': kind,
                 'processing_status': 'processed', 'fields': {
                     'registration_number': field('REG-100'),
                     'company_name': field('Sample Trading Ltd'),
                     **({'expiry_date': field('2026-10-18')} if kind == 'trade_license' else {})}}
                for kind in ('trade_license', 'business_registration')]}


def assess(data, **kwargs):
    return assess_risk(VendorSnapshot.model_validate(data), TODAY, **kwargs)


def test_complete_snapshot_is_deterministic_and_not_mutated(snapshot):
    original = deepcopy(snapshot)
    result = assess(snapshot)
    assert result.score == 100
    assert result.level == 'low_review_priority'
    assert result.findings == []
    assert result == assess(snapshot)
    assert snapshot == original


@pytest.mark.parametrize('expiry,score,code', [
    ('2026-10-17', 75, 'expired_license'),
    ('2026-10-18', 100, None), ('2026-10-19', 100, None),
    ('not-a-date', 90, 'unverified_mandatory_field'),
    ('2026-02-30', 90, 'unverified_mandatory_field'),
])
def test_expiry_boundary_and_invalid_dates(snapshot, expiry, score, code):
    snapshot['documents'][0]['fields']['expiry_date'] = field(expiry)
    result = assess(snapshot)
    assert result.score == score
    assert [f.code for f in result.findings] == ([code] if code else [])


def test_absent_documents_do_not_also_penalize_fields():
    result = assess({'vendor_id': 'v', 'company_name': '', 'documents': []})
    assert result.score == 40
    assert len(result.findings) == 2
    assert all(f.code == 'missing_required_document' for f in result.findings)


@pytest.mark.parametrize('status', ['unreviewed', 'confirmed', 'corrected'])
def test_only_reviewed_company_mismatch_counts(snapshot, status):
    snapshot['documents'][0]['fields']['company_name'] = field('Another Company', status)
    result = assess(snapshot)
    assert result.score == (90 if status == 'unreviewed' else 80)
    assert result.findings[0].code == (
        'unverified_mandatory_field' if status == 'unreviewed' else 'confirmed_company_name_mismatch')
    assert result.findings[0].evidence[0].document_id == 'trade_license'


def test_company_whitespace_case_normalization(snapshot):
    snapshot['documents'][0]['fields']['company_name'] = field(' SAMPLE   trading LTD ')
    assert assess(snapshot).score == 100


def test_raw_ocr_is_not_verified_and_registration_not_double_penalized(snapshot):
    snapshot['documents'][0]['fields']['registration_number'] = field('REG-100', 'unreviewed')
    snapshot['documents'][0]['fields']['expiry_date'] = field('2000-01-01', 'unreviewed')
    result = assess(snapshot)
    assert result.score == 75
    assert {f.code for f in result.findings} == {
        'missing_verified_registration', 'unverified_mandatory_field'}


@pytest.mark.parametrize('status', ['uploaded', 'processing', 'failed'])
def test_unprocessed_documents_do_not_assert_expiry_or_mismatch(snapshot, status):
    doc = snapshot['documents'][0]
    doc['processing_status'] = status
    doc['fields']['expiry_date'] = field('2000-01-01')
    doc['fields']['company_name'] = field('Other')
    result = assess(snapshot)
    assert result.score == 75
    assert not any(f.code in {'expired_license', 'confirmed_company_name_mismatch'} for f in result.findings)


def test_duplicates_preserve_evidence_without_duplicate_deduction(snapshot):
    doc = snapshot['documents'][0]
    doc['fields']['expiry_date'] = field('2000-01-01')
    duplicate = deepcopy(doc)
    duplicate['document_id'] = 'second-license'
    snapshot['documents'].append(duplicate)
    result = assess(snapshot)
    assert result.score == 75
    assert len(result.findings) == 1
    assert len(result.findings[0].evidence) == 2
    snapshot['documents'].reverse()
    assert assess(snapshot) == result


def test_score_clamps_and_config_is_versioned(snapshot):
    snapshot['documents'][0]['fields']['expiry_date'] = field('2000-01-01')
    result = assess(snapshot, rules=RiskRules(expired_license=150, version='custom-v2'))
    assert result.score == 0
    assert result.rules_version == 'custom-v2'


@pytest.mark.parametrize('score,level', [(100, 'low'), (80, 'low'), (79, 'medium'),
                                       (50, 'medium'), (49, 'high'), (0, 'high')])
def test_priority_boundaries(score, level):
    assert priority_for_score(score) == f'{level}_review_priority'


@pytest.mark.parametrize('value', [None, '', '   '])
def test_missing_registration_has_single_finding(snapshot, value):
    snapshot['documents'][0]['fields']['registration_number'] = field(value)
    result = assess(snapshot)
    assert result.score == 85
    assert len(result.findings) == 1
