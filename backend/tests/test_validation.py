import io

import pymupdf
import pytest

from app.core.errors import BadRequestError, PayloadTooLargeError
from app.ingestion.parsing import _clean_title, inspect_pdf, parse_pdf
from app.ingestion.validation import sanitize_filename, stream_to_file


def make_pdf(pages: list[str]) -> bytes:
    doc = pymupdf.open()
    for text in pages:
        page = doc.new_page()
        if text:
            page.insert_text((72, 72), text)
    data = doc.tobytes()
    doc.close()
    return data


def test_sanitize_filename_strips_path_and_unsafe_chars():
    assert sanitize_filename("../../etc/my paper?.pdf") == "my paper_.pdf"
    assert sanitize_filename("Attention.PDF") == "Attention.pdf"


def test_sanitize_filename_rejects_non_pdf():
    with pytest.raises(BadRequestError):
        sanitize_filename("notes.txt")


def test_stream_to_file_hashes_and_accepts_pdf(tmp_path):
    data = make_pdf(["hello"])
    stored = stream_to_file(io.BytesIO(data), tmp_path / "a.pdf", max_bytes=len(data))
    assert stored.size_bytes == len(data)
    assert len(stored.sha256) == 64


def test_stream_to_file_rejects_wrong_magic(tmp_path):
    with pytest.raises(BadRequestError):
        stream_to_file(io.BytesIO(b"PK\x03\x04 zip"), tmp_path / "a.pdf", max_bytes=1000)


def test_stream_to_file_enforces_size(tmp_path):
    with pytest.raises(PayloadTooLargeError):
        stream_to_file(io.BytesIO(b"%PDF-" + b"0" * 100), tmp_path / "a.pdf", max_bytes=50)


def test_stream_to_file_rejects_empty(tmp_path):
    with pytest.raises(BadRequestError):
        stream_to_file(io.BytesIO(b""), tmp_path / "a.pdf", max_bytes=50)


def test_inspect_pdf_rejects_corrupt_file(tmp_path):
    path = tmp_path / "broken.pdf"
    path.write_bytes(b"%PDF-1.7 not really a pdf")
    with pytest.raises(BadRequestError):
        inspect_pdf(path)


def test_parse_pdf_skips_empty_pages(tmp_path):
    path = tmp_path / "doc.pdf"
    path.write_bytes(make_pdf(["First page text", "", "Third page text"]))
    parsed = parse_pdf(path)
    assert parsed.page_count == 3
    assert [p.number for p in parsed.pages] == [1, 3]


def test_parse_pdf_with_no_text_returns_no_pages(tmp_path):
    path = tmp_path / "scan.pdf"
    path.write_bytes(make_pdf(["", ""]))
    assert parse_pdf(path).pages == []


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Attention Is All You Need", "Attention Is All You Need"),
        ("Microsoft Word - draft.docx", None),
        ("paper.pdf", None),
        ("untitled", None),
        ("", None),
        (None, None),
    ],
)
def test_clean_title(raw, expected):
    assert _clean_title(raw) == expected
