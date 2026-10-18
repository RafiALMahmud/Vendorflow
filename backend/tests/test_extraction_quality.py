from pathlib import Path

import pytest

from app.services import extraction
from app.services.extraction import (
    TesseractUnavailable,
    extract_document_text,
    parse_fictional_document,
)
from scripts.evaluate_extraction_quality import evaluate_corpus
from tests.fixtures.extraction_quality_corpus import FIELD_NAMES, QUALITY_DOCUMENTS


CORPUS_DIR = Path(__file__).parent / "fixtures" / "quality_documents"


def observed_fields(path: Path, mime_type: str) -> dict[str, str]:
    extracted = extract_document_text(path, mime_type)
    parsed = parse_fictional_document(extracted.text)
    return {
        field.field_name: field.normalized_value or field.raw_value for field in parsed
    }


def test_committed_digital_pdfs_exactly_match_ground_truth() -> None:
    digital_documents = [item for item in QUALITY_DOCUMENTS if not item.requires_ocr]
    exact_matches = 0
    expected_fields = 0

    for document in digital_documents:
        observed = observed_fields(CORPUS_DIR / document.filename, document.mime_type)
        expected_fields += len(document.expected)
        exact_matches += sum(
            observed.get(field_name) == expected_value
            for field_name, expected_value in document.expected.items()
        )

    assert len(digital_documents) == 2
    assert expected_fields == 12
    assert exact_matches == 12


def test_full_corpus_evaluator_uses_mocked_ocr_deterministically(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ocr_texts = iter(
        item.source_text for item in QUALITY_DOCUMENTS if item.requires_ocr
    )
    calls = 0

    def deterministic_ocr(image_bytes: bytes, settings) -> str:
        nonlocal calls
        calls += 1
        assert image_bytes.startswith(b"\x89PNG\r\n\x1a\n")
        return next(ocr_texts)

    monkeypatch.setattr(extraction, "_run_tesseract", deterministic_ocr)

    report = evaluate_corpus(CORPUS_DIR)

    assert report["documents"] == {
        "total": 4,
        "successfully_evaluated": 4,
        "failed": 0,
    }
    assert report["overall"] == {
        "exact_matches": 24,
        "expected_fields": 24,
        "accuracy": 1.0,
    }
    assert report["failure_categories"] == {}
    assert calls == 2
    assert set(report["per_field"]) == set(FIELD_NAMES)
    assert all(
        item == {"exact_matches": 4, "expected": 4, "accuracy": 1.0}
        for item in report["per_field"].values()
    )


def test_unavailable_ocr_counts_as_failures_in_overall_denominator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unavailable_ocr(image_bytes: bytes, settings) -> str:
        raise TesseractUnavailable("Tesseract unavailable for deterministic test")

    monkeypatch.setattr(extraction, "_run_tesseract", unavailable_ocr)

    report = evaluate_corpus(CORPUS_DIR)

    assert report["documents"]["failed"] == 2
    assert report["overall"] == {
        "exact_matches": 12,
        "expected_fields": 24,
        "accuracy": 0.5,
    }
    assert report["failure_categories"] == {"ocr_unavailable": 2}
    assert all(item["expected"] == 4 for item in report["per_field"].values())
