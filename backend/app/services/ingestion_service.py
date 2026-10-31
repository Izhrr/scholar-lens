import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import delete
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.core.errors import AppError
from app.db.models import IngestionJob, JobStatus, Paper, PaperChunk, PaperStatus
from app.generation.openai_client import OpenAIGateway
from app.ingestion.chunking import chunk_pages
from app.ingestion.parsing import parse_pdf
from app.retrieval.bm25 import BM25Index
from app.retrieval.vector_store import ChunkVector, VectorStore

logger = logging.getLogger(__name__)

SCANNED_OR_EMPTY_PDF = (
    "SCANNED_OR_EMPTY_PDF: no extractable text was found. Scanned PDFs need OCR first, "
    "which ScholarLens does not do yet. Export a text-based PDF and upload it again."
)
UNEXPECTED_FAILURE = (
    "Indexing failed unexpectedly. Retry; if it fails again, check the backend logs."
)


class IngestionError(AppError):
    pass


class IngestionService:
    """Runs one ingestion job end to end. Owns its DB session because it runs after the request."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        settings: Settings,
        openai_gateway: OpenAIGateway,
        vector_store: VectorStore,
        bm25: BM25Index,
    ) -> None:
        self._session_factory = session_factory
        self._settings = settings
        self._openai = openai_gateway
        self._vectors = vector_store
        self._bm25 = bm25

    def run(self, job_id: uuid.UUID) -> None:
        with self._session_factory() as db:
            job = db.get(IngestionJob, job_id)
            if job is None or job.status != JobStatus.QUEUED:
                return
            paper = job.paper
            if paper.status != PaperStatus.QUEUED:
                return

            job.status = JobStatus.PROCESSING
            job.started_at = datetime.now(UTC)
            paper.status = PaperStatus.PROCESSING
            db.commit()

            try:
                self._index(db, paper)
            except Exception as exc:
                self._fail(db, job_id, paper.id, exc)
                return

            job.status = JobStatus.SUCCEEDED
            job.finished_at = datetime.now(UTC)
            db.commit()
            self._bm25.rebuild(db)
            logger.info("Indexed paper %s (%d chunks)", paper.id, paper.chunk_count)

    def _index(self, db: Session, paper: Paper) -> None:
        s = self._settings
        parsed = parse_pdf(s.papers_dir / paper.file_path)
        paper.page_count = parsed.page_count
        # Commit now so the page count survives a later rollback on failure.
        db.commit()
        if not parsed.pages:
            raise IngestionError(SCANNED_OR_EMPTY_PDF)

        chunks = chunk_pages(parsed.pages, s.chunk_size, s.chunk_overlap)
        if not chunks:
            raise IngestionError(SCANNED_OR_EMPTY_PDF)

        rows = [
            PaperChunk(
                id=uuid.uuid4(),
                paper_id=paper.id,
                chunk_index=chunk.chunk_index,
                page_number=chunk.page_number,
                content=chunk.content,
                char_start=chunk.char_start,
                char_end=chunk.char_end,
            )
            for chunk in chunks
        ]
        db.add_all(rows)
        db.flush()

        embeddings = self._openai.embed_documents([row.content for row in rows])
        self._vectors.upsert(
            [
                ChunkVector(
                    chunk_id=row.id,
                    paper_id=paper.id,
                    page_number=row.page_number,
                    chunk_index=row.chunk_index,
                    content=row.content,
                    embedding=embedding,
                )
                for row, embedding in zip(rows, embeddings, strict=True)
            ],
            embedding_model=self._openai.embedding_model,
        )

        stored = self._vectors.count_for_paper(paper.id)
        if stored != len(rows):
            raise IngestionError(
                f"Vector store holds {stored} of {len(rows)} chunks. Retry to re-index."
            )

        paper.chunk_count = len(rows)
        paper.status = PaperStatus.INDEXED
        paper.error_message = None
        paper.embedding_model = self._openai.embedding_model
        paper.chunking_version = s.chunking_version

    def _fail(self, db: Session, job_id: uuid.UUID, paper_id: uuid.UUID, exc: Exception) -> None:
        db.rollback()
        message = exc.detail if isinstance(exc, AppError) else UNEXPECTED_FAILURE
        if isinstance(exc, AppError):
            logger.warning("Ingestion of paper %s failed: %s", paper_id, message)
        else:
            logger.exception("Ingestion of paper %s failed", paper_id)

        try:
            self._vectors.delete_paper(paper_id)
        except Exception:
            logger.warning(
                "Could not remove partial vectors for paper %s; retry cleans up", paper_id
            )

        db.execute(delete(PaperChunk).where(PaperChunk.paper_id == paper_id))
        job = db.get(IngestionJob, job_id)
        paper = db.get(Paper, paper_id)
        if job is not None:
            job.status = JobStatus.FAILED
            job.error_message = message
            job.finished_at = datetime.now(UTC)
        if paper is not None:
            paper.status = PaperStatus.FAILED
            paper.error_message = message
            paper.chunk_count = 0
        db.commit()
