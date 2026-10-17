"""Generate the committed fictional extraction-quality corpus."""

import json
from pathlib import Path

from tests.fixtures.extraction_quality_corpus import QUALITY_DOCUMENTS, document_bytes


DEFAULT_OUTPUT = Path(__file__).parents[1] / "tests" / "fixtures" / "quality_documents"


def generate(output_dir: Path = DEFAULT_OUTPUT) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, object]] = []
    for document in QUALITY_DOCUMENTS:
        (output_dir / document.filename).write_bytes(document_bytes(document))
        manifest.append(
            {
                "name": document.name,
                "filename": document.filename,
                "mime_type": document.mime_type,
                "requires_ocr": document.requires_ocr,
                "expected": document.expected,
            }
        )
    manifest_path = output_dir / "ground_truth.json"
    manifest_path.write_text(
        json.dumps({"documents": manifest}, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest_path


if __name__ == "__main__":
    print(generate())
