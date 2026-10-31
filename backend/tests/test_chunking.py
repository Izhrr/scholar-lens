from app.ingestion.chunking import chunk_pages
from app.ingestion.parsing import ParsedPage


def test_chunks_never_cross_pages_and_indexes_are_global():
    pages = [
        ParsedPage(number=1, text="alpha " * 300),
        ParsedPage(number=4, text="beta " * 300),
    ]
    chunks = chunk_pages(pages, chunk_size=200, chunk_overlap=20)

    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))
    assert {c.page_number for c in chunks} == {1, 4}
    for chunk in chunks:
        word = "alpha" if chunk.page_number == 1 else "beta"
        assert set(chunk.content.split()) == {word}
        assert len(chunk.content) <= 200
        assert chunk.char_end >= chunk.char_start >= 0


def test_short_page_is_one_chunk():
    chunks = chunk_pages([ParsedPage(number=2, text="Short page.")], 800, 120)
    assert len(chunks) == 1
    assert chunks[0].page_number == 2
    assert chunks[0].content == "Short page."
