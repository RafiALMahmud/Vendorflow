from dataclasses import dataclass
from datetime import datetime
import logging
from pathlib import Path
import re
import shutil
import subprocess
from uuid import UUID

import pymupdf
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.documents import (
    Document,
    ExtractedField,
    ProcessingStatus,
    ReviewStatus,
)
from app.services.document_storage import resolve_storage_path

logger = logging.getLogger(__name__)

PDF_TEXT_METHOD = "pdf_text"
OCR_METHOD = "tesseract_ocr"
DATE_FIELDS = {"issue_date", "expiry_date"}
FIELD_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "company_name": (
        re.compile(r"(?im)^\s*(?:company|business)\s+name\s*[:\-]\s*(?P<value>[^\r\n]+)"),
    ),
    "registration_number": (
        re.compile(r"(?im)^\s*(?:registration|reg\.?)[\s#]*(?:number|no\.?)?\s*[:\-]\s*(?P<value>[^\r\n]+)"),
    ),
    "license_number": (
        re.compile(r"(?im)^\s*(?:trade\s+)?licen[cs]e[\s#]*(?:number|no\.?)?\s*[:\-]\s*(?P<value>[^\r\n]+)"),
    ),
    "issue_date": (
        re.compile(r"(?im)^\s*(?:issue|issued)\s+date\s*[:\-]\s*(?P<value>[^\r\n]+)"),
    ),
    "expiry_date": (
        re.compile(r"(?im)^\s*(?:expiry|expiration|expires?)\s+date\s*[:\-]\s*(?P<value>[^\r\n]+)"),
    ),
    "tax_identifier": (
        re.compile(r"(?im)^\s*(?:tax\s+(?:identifier|id)|tin)[\s#]*(?:number|no\.?)?\s*[:\-]\s*(?P<value>[^\r\n]+)"),
    ),
}


class ExtractionFailure(Exception):
    """A safe, user-facing extraction failure without document contents."""


class TesseractUnavailable(ExtractionFailure):
    pass


@dataclass(frozen=True)
class ExtractedText:
    text: str
    method: str


@dataclass(frozen=True)
class ParsedField:
    field_name: str
    raw_value: str
    normalized_value: str | None = None
    review_note: str | None = None


def _tesseract_executable(settings: Settings) -> str:
    if settings.tesseract_cmd is not None:
        configured = settings.tesseract_cmd.expanduser()
        if configured.is_file():
            return str(configured.resolve())
        raise TesseractUnavailable(
            "Tesseract OCR is configured but unavailable. Fix TESSERACT_CMD and "
            "re-upload this document."
        )

    discovered = shutil.which("tesseract")
    if discovered is None:
        raise TesseractUnavailable(
            "This scan requires Tesseract OCR, but Tesseract is not installed or "
            "not on PATH. Install it, restart the backend, and re-upload the document."
        )
    return discovered


def _run_tesseract(image_bytes: bytes, settings: Settings) -> str:
    executable = _tesseract_executable(settings)
    try:
        result = subprocess.run(
            [
                executable,
                "stdin",
                "stdout",
                "-l",
                settings.tesseract_language,
                "--psm",
                "6",
            ],
            input=image_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=settings.tesseract_timeout_seconds,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ExtractionFailure(
            "Tesseract OCR could not complete. Check the installation and re-upload "
            "a clear document."
        ) from exc

    if result.returncode != 0:
        raise ExtractionFailure(
            "Tesseract OCR could not read this document. Re-upload a clearer scan."
        )
    return result.stdout.decode("utf-8", errors="replace").strip()


def _extract_pdf_text(path: Path, settings: Settings) -> ExtractedText:
    try:
        with pymupdf.open(path) as pdf:
            if pdf.needs_pass or pdf.page_count < 1:
                raise ExtractionFailure(
                    "The PDF is encrypted or unreadable. Upload an unlocked, valid PDF."
                )
            if pdf.page_count > settings.extraction_max_pdf_pages:
                raise ExtractionFailure(
                    f"The PDF exceeds the {settings.extraction_max_pdf_pages}-page "
                    "processing limit. Upload a shorter document."
                )

            selectable_text = "\n".join(page.get_text("text") for page in pdf).strip()
            if selectable_text:
                return ExtractedText(selectable_text, PDF_TEXT_METHOD)

            ocr_text: list[str] = []
            scale = 200 / 72
            for page in pdf:
                image_bytes = page.get_pixmap(
                    matrix=pymupdf.Matrix(scale, scale),
                    alpha=False,
                ).tobytes("png")
                page_text = _run_tesseract(image_bytes, settings)
                if page_text:
                    ocr_text.append(page_text)
    except ExtractionFailure:
        raise
    except (pymupdf.FileDataError, OSError, RuntimeError, ValueError) as exc:
        raise ExtractionFailure(
            "The PDF became unreadable during processing. Re-upload a valid PDF."
        ) from exc

    combined = "\n".join(ocr_text).strip()
    if not combined:
        raise ExtractionFailure(
            "No readable text was found. Re-upload a clearer scan for human review."
        )
    return ExtractedText(combined, OCR_METHOD)


def extract_document_text(
    path: Path,
    mime_type: str,
    settings: Settings | None = None,
) -> ExtractedText:
    active_settings = settings or get_settings()
    if mime_type == "application/pdf":
        return _extract_pdf_text(path, active_settings)
    if mime_type in {"image/jpeg", "image/png"}:
        try:
            image_bytes = path.read_bytes()
        except OSError as exc:
            raise ExtractionFailure(
                "The image could not be read. Re-upload a valid image."
            ) from exc
        text = _run_tesseract(image_bytes, active_settings).strip()
        if not text:
            raise ExtractionFailure(
                "No readable text was found. Re-upload a clearer image for human review."
            )
        return ExtractedText(text, OCR_METHOD)
    raise ExtractionFailure("This stored document type is not supported for extraction.")


def normalize_date(raw_value: str) -> tuple[str | None, str | None]:
    value = re.sub(r"\s+", " ", raw_value.strip())
    named_formats = (
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d %B %Y",
        "%d %b %Y",
        "%B %d %Y",
        "%b %d %Y",
        "%B %d, %Y",
        "%b %d, %Y",
    )
    for date_format in named_formats:
        try:
            return datetime.strptime(value, date_format).date().isoformat(), None
        except ValueError:
            continue

    numeric = re.fullmatch(r"(\d{1,4})[./-](\d{1,2})[./-](\d{1,4})", value)
    if numeric:
        first, second, third = (int(part) for part in numeric.groups())
        try:
            if len(numeric.group(1)) == 4:
                return datetime(first, second, third).date().isoformat(), None
            if len(numeric.group(3)) == 4:
                if first > 12 >= second:
                    return datetime(third, second, first).date().isoformat(), None
                if second > 12 >= first:
                    return datetime(third, first, second).date().isoformat(), None
                if first == second:
                    return datetime(third, first, second).date().isoformat(), None
                if first <= 12 and second <= 12:
                    return None, "Ambiguous numeric date; confirm the day/month order."
        except ValueError:
            pass

    return None, "Date could not be normalized; review the original value manually."


def parse_fictional_document(text: str) -> list[ParsedField]:
    parsed: list[ParsedField] = []
    for field_name, patterns in FIELD_PATTERNS.items():
        match = None
        for pattern in patterns:
            match = pattern.search(text)
            if match is not None:
                break
        if match is None:
            continue
        raw_value = match.group("value").strip().strip("|;")
        if not raw_value:
            continue
        normalized_value = None
        review_note = None
        if field_name in DATE_FIELDS:
            normalized_value, review_note = normalize_date(raw_value)
        parsed.append(
            ParsedField(
                field_name=field_name,
                raw_value=raw_value,
                normalized_value=normalized_value,
                review_note=review_note,
            )
        )
    return parsed


def process_document(
    document_id: UUID,
    db: Session,
    settings: Settings | None = None,
) -> Document:
    active_settings = settings or get_settings()
    document = db.get(Document, document_id)
    if document is None:
        raise ValueError("Document does not exist")

    document.processing_status = ProcessingStatus.PROCESSING
    document.processing_error = None
    db.execute(delete(ExtractedField).where(ExtractedField.document_id == document.id))
    db.commit()

    try:
        path = resolve_storage_path(document.storage_key, active_settings)
        extracted = extract_document_text(path, document.mime_type, active_settings)
        fields = parse_fictional_document(extracted.text)
        for field in fields:
            db.add(
                ExtractedField(
                    document_id=document.id,
                    field_name=field.field_name,
                    raw_value=field.raw_value,
                    normalized_value=field.normalized_value,
                    confirmed_value=None,
                    review_status=ReviewStatus.UNREVIEWED,
                    extraction_method=extracted.method,
                    review_note=field.review_note,
                )
            )
        document.processing_status = ProcessingStatus.PROCESSED
        document.processing_error = None
        db.commit()
    except ExtractionFailure as exc:
        db.rollback()
        document = db.get(Document, document_id)
        if document is None:
            raise
        document.processing_status = ProcessingStatus.FAILED
        document.processing_error = str(exc)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Unexpected extraction failure for document %s", document_id)
        document = db.get(Document, document_id)
        if document is None:
            raise
        document.processing_status = ProcessingStatus.FAILED
        document.processing_error = (
            "Document processing failed safely. Re-upload the document or contact support."
        )
        db.commit()

    db.refresh(document)
    return document


def extracted_fields_for_document(document_id: UUID, db: Session) -> list[ExtractedField]:
    return list(
        db.scalars(
            select(ExtractedField)
            .where(ExtractedField.document_id == document_id)
            .order_by(ExtractedField.field_name)
        )
    )
