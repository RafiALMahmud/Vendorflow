from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import pymupdf
from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError

from app.core.config import Settings

CHUNK_SIZE = 64 * 1024
ALLOWED_EXTENSIONS = {
    ".pdf": ("application/pdf", {"application/pdf"}),
    ".jpg": ("image/jpeg", {"image/jpeg", "image/jpg"}),
    ".jpeg": ("image/jpeg", {"image/jpeg", "image/jpg"}),
    ".png": ("image/png", {"image/png"}),
}
CANONICAL_EXTENSIONS = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
}


class UploadValidationError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


@dataclass(frozen=True)
class StoredUpload:
    storage_key: str
    original_filename: str
    mime_type: str
    file_size: int


def storage_root(settings: Settings) -> Path:
    configured = settings.document_storage_dir.expanduser()
    if not configured.is_absolute():
        configured = Path(__file__).resolve().parents[3] / configured
    root = configured.resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _validate_filename(upload: UploadFile) -> tuple[str, str]:
    filename = upload.filename or ""
    if (
        not filename
        or len(filename) > 255
        or filename in {".", ".."}
        or "/" in filename
        or "\\" in filename
    ):
        raise UploadValidationError(400, "Filename must be a plain file name")

    extension = Path(filename).suffix.casefold()
    allowed = ALLOWED_EXTENSIONS.get(extension)
    if allowed is None:
        raise UploadValidationError(
            415,
            "Unsupported file type; upload PDF, JPG, JPEG, or PNG",
        )
    canonical_mime, accepted_declared_types = allowed
    declared_type = (upload.content_type or "").split(";", 1)[0].strip().casefold()
    if declared_type not in accepted_declared_types:
        raise UploadValidationError(415, "File extension and content type do not match")
    return filename, canonical_mime


def _detect_mime(path: Path) -> str | None:
    with path.open("rb") as stored_file:
        header = stored_file.read(16)
    if header.startswith(b"%PDF-"):
        return "application/pdf"
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    return None


def _validate_file_structure(path: Path, mime_type: str) -> None:
    try:
        if mime_type == "application/pdf":
            with pymupdf.open(stream=path.read_bytes(), filetype="pdf") as document:
                if document.needs_pass or document.page_count < 1:
                    raise ValueError("Unreadable PDF")
                document.load_page(0)
            return

        expected_format = "JPEG" if mime_type == "image/jpeg" else "PNG"
        with Image.open(path) as image:
            if image.format != expected_format:
                raise ValueError("Image format mismatch")
            image.verify()
    except (pymupdf.FileDataError, UnidentifiedImageError, OSError, RuntimeError, ValueError) as exc:
        raise UploadValidationError(400, "File is corrupt or unreadable") from exc


async def store_validated_upload(
    upload: UploadFile,
    settings: Settings,
) -> StoredUpload:
    filename, expected_mime = _validate_filename(upload)
    root = storage_root(settings)
    temporary_path = root / f".{uuid4().hex}.part"
    file_size = 0

    try:
        with temporary_path.open("xb") as destination:
            while chunk := await upload.read(CHUNK_SIZE):
                file_size += len(chunk)
                if file_size > settings.document_max_file_size_bytes:
                    raise UploadValidationError(
                        413,
                        f"File exceeds the {settings.document_max_file_size_bytes}-byte limit",
                    )
                destination.write(chunk)

        if file_size == 0:
            raise UploadValidationError(400, "File is empty")

        detected_mime = _detect_mime(temporary_path)
        if detected_mime is None or detected_mime != expected_mime:
            raise UploadValidationError(415, "File signature does not match its type")
        _validate_file_structure(temporary_path, detected_mime)

        storage_key = f"{uuid4().hex}{CANONICAL_EXTENSIONS[detected_mime]}"
        temporary_path.replace(root / storage_key)
        return StoredUpload(
            storage_key=storage_key,
            original_filename=filename,
            mime_type=detected_mime,
            file_size=file_size,
        )
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()


def resolve_storage_path(storage_key: str, settings: Settings) -> Path:
    root = storage_root(settings)
    if not storage_key or Path(storage_key).name != storage_key:
        raise FileNotFoundError("Invalid storage key")
    candidate = (root / storage_key).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise FileNotFoundError("Invalid storage key") from exc
    if not candidate.is_file():
        raise FileNotFoundError("Stored document is missing")
    return candidate


def delete_stored_file(storage_key: str, settings: Settings) -> None:
    try:
        resolve_storage_path(storage_key, settings).unlink(missing_ok=True)
    except FileNotFoundError:
        pass
