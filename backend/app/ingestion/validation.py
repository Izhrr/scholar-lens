import hashlib
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from app.core.errors import BadRequestError, PayloadTooLargeError

PDF_MAGIC = b"%PDF-"
_READ_CHUNK = 1024 * 1024
_UNSAFE_CHARS = re.compile(r"[^\w.\- ()\[\]]+")


@dataclass(frozen=True)
class StoredUpload:
    path: Path
    sha256: str
    size_bytes: int


def sanitize_filename(raw: str | None) -> str:
    """Return a display-safe filename. Stored files never use this name on disk."""
    name = Path(raw or "").name
    name = unicodedata.normalize("NFKC", name)
    name = "".join(ch for ch in name if unicodedata.category(ch)[0] != "C")
    name = _UNSAFE_CHARS.sub("_", name).strip(" .")
    if not name.lower().endswith(".pdf"):
        raise BadRequestError("Only .pdf files are accepted.")
    stem = name[:-4][:200] or "paper"
    return f"{stem}.pdf"


def stream_to_file(source: BinaryIO, destination: Path, max_bytes: int) -> StoredUpload:
    """Copy an upload to disk while hashing it, enforcing size and PDF signature."""
    digest = hashlib.sha256()
    size = 0
    head = b""
    with destination.open("wb") as out:
        while block := source.read(_READ_CHUNK):
            size += len(block)
            if size > max_bytes:
                raise PayloadTooLargeError(
                    f"File is larger than the {max_bytes // (1024 * 1024)} MB limit."
                )
            if len(head) < len(PDF_MAGIC):
                head += block[: len(PDF_MAGIC) - len(head)]
            digest.update(block)
            out.write(block)

    if size == 0:
        raise BadRequestError("The uploaded file is empty.")
    if head != PDF_MAGIC:
        raise BadRequestError("This file is not a PDF (missing %PDF- header).")
    return StoredUpload(path=destination, sha256=digest.hexdigest(), size_bytes=size)
