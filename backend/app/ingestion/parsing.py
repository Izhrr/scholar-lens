import logging
from dataclasses import dataclass
from pathlib import Path

import pymupdf

from app.core.errors import BadRequestError

logger = logging.getLogger(__name__)

_GENERIC_TITLES = {"untitled", "title", "document", "microsoft word", "pdf"}


@dataclass(frozen=True)
class ParsedPage:
    number: int  # 1-based
    text: str


@dataclass(frozen=True)
class ParsedPdf:
    page_count: int
    pages: list[ParsedPage]  # only pages with extractable text
    metadata_title: str | None


def inspect_pdf(path: Path) -> tuple[int, str | None]:
    """Open the PDF once at upload time to reject corrupt files early."""
    try:
        with pymupdf.open(path) as doc:
            if doc.needs_pass:
                raise BadRequestError("Password-protected PDFs are not supported.")
            return doc.page_count, _clean_title(doc.metadata.get("title") if doc.metadata else None)
    except BadRequestError:
        raise
    except Exception as exc:
        raise BadRequestError("The PDF could not be opened. It may be corrupt.") from exc


def parse_pdf(path: Path) -> ParsedPdf:
    with pymupdf.open(path) as doc:
        pages = []
        for index, page in enumerate(doc):
            text = _normalize(page.get_text("text", sort=True))
            if text:
                pages.append(ParsedPage(number=index + 1, text=text))
        title = _clean_title(doc.metadata.get("title") if doc.metadata else None)
        page_count = doc.page_count

    skipped = page_count - len(pages)
    if skipped:
        logger.info("Skipped %d page(s) without extractable text in %s", skipped, path.name)
    return ParsedPdf(page_count=page_count, pages=pages, metadata_title=title)


def _normalize(text: str) -> str:
    # Re-join words hyphenated across line breaks, then collapse layout whitespace.
    text = text.replace("-\n", "")
    lines = [" ".join(line.split()) for line in text.splitlines()]
    paragraphs, current = [], []
    for line in lines:
        if line:
            current.append(line)
        elif current:
            paragraphs.append(" ".join(current))
            current = []
    if current:
        paragraphs.append(" ".join(current))
    return "\n\n".join(paragraphs).strip()


def _clean_title(raw: str | None) -> str | None:
    if not raw:
        return None
    title = " ".join(raw.split())
    lowered = title.lower()
    if not 6 <= len(title) <= 300:
        return None
    if lowered in _GENERIC_TITLES or lowered.startswith("microsoft word"):
        return None
    if lowered.endswith((".pdf", ".doc", ".docx", ".tex", ".dvi")):
        return None
    return title
