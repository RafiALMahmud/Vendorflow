"""Measure exact-match extraction quality on the fictional committed corpus."""

from collections import Counter
import json
from pathlib import Path
import platform
from typing import Any

import pymupdf

from app.core.config import Settings, get_settings
from app.services.extraction import (
    DATE_FIELDS,
    ExtractionFailure,
    TesseractUnavailable,
    extract_document_text,
    parse_fictional_document,
)
from scripts.generate_extraction_quality_fixtures import DEFAULT_OUTPUT


def _accuracy(matches: int, expected: int) -> float:
    return round(matches / expected, 6) if expected else 0.0


def evaluate_corpus(
    corpus_dir: Path = DEFAULT_OUTPUT,
    settings: Settings | None = None,
) -> dict[str, Any]:
    active_settings = settings or get_settings()
    manifest = json.loads(
        (corpus_dir / "ground_truth.json").read_text(encoding="utf-8")
    )
    field_totals: dict[str, dict[str, int]] = {}
    failures: Counter[str] = Counter()
    document_results: list[dict[str, Any]] = []
    total_expected = 0
    total_matches = 0
    successful_documents = 0

    for document in manifest["documents"]:
        expected: dict[str, str] = document["expected"]
        total_expected += len(expected)
        for field_name in expected:
            field_totals.setdefault(field_name, {"exact_matches": 0, "expected": 0})
            field_totals[field_name]["expected"] += 1

        path = corpus_dir / document["filename"]
        result: dict[str, Any] = {
            "name": document["name"],
            "filename": document["filename"],
            "requires_ocr": document["requires_ocr"],
            "expected_fields": len(expected),
            "exact_matches": 0,
            "status": "failed",
            "extraction_method": None,
            "failures": [],
        }
        try:
            extracted = extract_document_text(path, document["mime_type"], active_settings)
            parsed = {
                field.field_name: field for field in parse_fictional_document(extracted.text)
            }
        except TesseractUnavailable:
            failures["ocr_unavailable"] += 1
            result["failures"].append("ocr_unavailable")
        except ExtractionFailure:
            failures["extraction_failure"] += 1
            result["failures"].append("extraction_failure")
        except Exception:
            failures["unexpected_safe_failure"] += 1
            result["failures"].append("unexpected_safe_failure")
        else:
            successful_documents += 1
            result["status"] = "evaluated"
            result["extraction_method"] = extracted.method
            for field_name, expected_value in expected.items():
                candidate = parsed.get(field_name)
                if candidate is None:
                    failures["missing_field"] += 1
                    result["failures"].append(f"missing_field:{field_name}")
                    continue
                observed = (
                    candidate.normalized_value
                    if field_name in DATE_FIELDS and candidate.normalized_value is not None
                    else candidate.raw_value
                )
                if observed == expected_value:
                    total_matches += 1
                    result["exact_matches"] += 1
                    field_totals[field_name]["exact_matches"] += 1
                else:
                    failures["value_mismatch"] += 1
                    result["failures"].append(f"value_mismatch:{field_name}")
            unexpected_fields = sorted(set(parsed) - set(expected))
            if unexpected_fields:
                failures["unexpected_field"] += len(unexpected_fields)
                result["failures"].extend(
                    f"unexpected_field:{field_name}" for field_name in unexpected_fields
                )
        document_results.append(result)

    per_field = {
        field_name: {
            **counts,
            "accuracy": _accuracy(counts["exact_matches"], counts["expected"]),
        }
        for field_name, counts in sorted(field_totals.items())
    }
    return {
        "metric_definition": "exactly_matched_fields / expected_fields",
        "environment": {
            "python": platform.python_version(),
            "pymupdf": pymupdf.version[0],
        },
        "documents": {
            "total": len(manifest["documents"]),
            "successfully_evaluated": successful_documents,
            "failed": len(manifest["documents"]) - successful_documents,
        },
        "overall": {
            "exact_matches": total_matches,
            "expected_fields": total_expected,
            "accuracy": _accuracy(total_matches, total_expected),
        },
        "per_field": per_field,
        "failure_categories": dict(sorted(failures.items())),
        "document_results": document_results,
    }


if __name__ == "__main__":
    print(json.dumps(evaluate_corpus(), indent=2))
