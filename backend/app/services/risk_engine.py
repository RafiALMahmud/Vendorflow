"""Deterministic completeness checks. No IO, implicit clock, or automatic decisions."""

from datetime import date

from app.schemas.risk import Evidence, Finding, RiskAssessment, RiskRules, VendorSnapshot


def priority_for_score(score: int) -> str:
    return ('low_review_priority' if score >= 80 else
            'medium_review_priority' if score >= 50 else 'high_review_priority')


def assess_risk(snapshot: VendorSnapshot, reference_date: date,
                rules: RiskRules | None = None) -> RiskAssessment:
    rules = rules or RiskRules()
    findings: dict[tuple[str, str, str | None], Finding] = {}

    def add(code: str, description: str, deduction: int, evidence: Evidence) -> None:
        # Same condition on duplicate documents is deducted once per type/field.
        key = (code, evidence.document_type, evidence.field_name)
        if key not in findings:
            findings[key] = Finding(code=code, severity='error' if code in {
                'missing_required_document', 'expired_license'} else 'warning',
                description=description, deduction=deduction, evidence=[])
        if evidence not in findings[key].evidence:
            findings[key].evidence.append(evidence)

    present = {doc.document_type for doc in snapshot.documents}
    for kind in sorted(set(rules.required_documents) - present):
        add('missing_required_document', f'Required {kind} document is absent.',
            rules.missing_document, Evidence(document_type=kind))

    for doc in sorted(snapshot.documents, key=lambda d: (d.document_type, d.document_id)):
        def evidence(field: str) -> Evidence:
            return Evidence(document_type=doc.document_type,
                            document_id=doc.document_id, field_name=field)

        mandatory = ['registration_number'] if doc.document_type in rules.required_documents else []
        if doc.document_type == 'trade_license':
            mandatory.append('expiry_date')
        for field in mandatory:
            value = doc.fields.get(field)
            verified = value.verified_value if value and doc.processing_status == 'processed' else None
            if not verified:
                registration = field == 'registration_number'
                add('missing_verified_registration' if registration else 'unverified_mandatory_field',
                    f'{field} requires a readable, confirmed value on a processed document.',
                    rules.missing_registration if registration else rules.unverified_field,
                    evidence(field))
        if doc.processing_status != 'processed':
            continue
        company = doc.fields.get('company_name')
        if company and company.verified_value:
            normalize = lambda value: ' '.join(value.casefold().split())
            if normalize(company.verified_value) != normalize(snapshot.company_name):
                add('confirmed_company_name_mismatch',
                    'Confirmed document company name differs from the vendor profile.',
                    rules.company_mismatch, evidence('company_name'))
        elif company:
            add('unverified_mandatory_field', 'Document company name requires confirmation.',
                rules.unverified_field, evidence('company_name'))
        expiry = doc.fields.get('expiry_date')
        if doc.document_type == 'trade_license' and expiry and expiry.verified_value:
            try:
                expiry_date = date.fromisoformat(expiry.verified_value)
            except ValueError:
                add('unverified_mandatory_field', 'License expiry is not a valid ISO date.',
                    rules.unverified_field, evidence('expiry_date'))
            else:
                if expiry_date < reference_date:
                    add('expired_license', 'Confirmed license expired before the reference date.',
                        rules.expired_license, evidence('expiry_date'))

    result = [findings[key] for key in sorted(findings)]
    score = max(0, min(100, 100 - sum(item.deduction for item in result)))
    return RiskAssessment(score=score, level=priority_for_score(score), findings=result,
                          rules_version=rules.version, reference_date=reference_date)
