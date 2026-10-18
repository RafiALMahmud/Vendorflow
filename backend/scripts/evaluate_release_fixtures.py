"""Measure the supplied four fictional PDFs using the actual extraction pipeline."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from app.services.extraction import ExtractionFailure, extract_document_text, parse_fictional_document

CORPUS = Path(__file__).resolve().parents[1] / 'tests/fixtures/vendorflow_qa'


def evaluate():
    manifest = json.loads((CORPUS / 'expected_results.json').read_text())
    records = []
    for item in manifest['documents']:
        row = {'file': item['file'], 'expected': item['expected'], 'expected_fields': len(item['expected'])}
        try:
            text = extract_document_text(CORPUS / item['file'], 'application/pdf')
            actual = {field.field_name: field.normalized_value or field.raw_value for field in parse_fictional_document(text.text)}
            matches = sum(actual.get(key) == value for key, value in item['expected'].items())
            row.update(method=text.method, observed=actual, matches=matches,
                       status='PASS' if matches == len(item['expected']) else 'FAIL')
        except ExtractionFailure as exc:
            row.update(status='BLOCKED', observed={}, matches=0, error=str(exc))
        records.append(row)
    return {'reference_date': manifest['reference_date'], 'executed_at_utc': datetime.now(timezone.utc).isoformat(),
            'fictional_small_sample_only': True, 'documents': records,
            'exact_matches': sum(row['matches'] for row in records),
            'expected_fields': sum(row['expected_fields'] for row in records)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    options = parser.parse_args()
    report = evaluate()
    if options.output:
        options.output.parent.mkdir(parents=True, exist_ok=True)
        options.output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if all(row['status'] == 'PASS' for row in report['documents']) else 1)
