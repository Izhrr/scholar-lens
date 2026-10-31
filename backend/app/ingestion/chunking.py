from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.ingestion.parsing import ParsedPage


@dataclass(frozen=True)
class TextChunk:
    chunk_index: int
    page_number: int
    content: str
    char_start: int
    char_end: int


def chunk_pages(pages: list[ParsedPage], chunk_size: int, chunk_overlap: int) -> list[TextChunk]:
    """Split each page on its own so every chunk maps to exactly one citable page."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        add_start_index=True,
    )
    chunks: list[TextChunk] = []
    for page in pages:
        for doc in splitter.create_documents([page.text]):
            content = doc.page_content.strip()
            if not content:
                continue
            start = doc.metadata.get("start_index", 0)
            chunks.append(
                TextChunk(
                    chunk_index=len(chunks),
                    page_number=page.number,
                    content=content,
                    char_start=start,
                    char_end=start + len(doc.page_content),
                )
            )
    return chunks
