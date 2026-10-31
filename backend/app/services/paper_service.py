import logging
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import ConflictError, DependencyUnavailableError, NotFoundError
from app.db.models import IngestionJob, JobStatus, Paper, PaperChunk, PaperStatus
from app.ingestion.parsing import inspect_pdf
from app.ingestion.validation import sanitize_filename, stream_to_file
from app.retrieval.bm25 import BM25Index
from app.retrieval.vector_store import VectorStore

logger = logging.getLogger(__name__)

RESTART_MESSAGE = "Indexing was interrupted by a backend restart. Retry to index it again."


class PaperService:
    def __init__(
        self, db: Session, settings: Settings, vector_store: VectorStore, bm25: BM25Index
    ) -> None:
        self._db = db
        self._settings = settings
        self._vectors = vector_store
        self._bm25 = bm25

    @property
    def _papers_dir(self) -> Path:
        return self._settings.papers_dir

    def list(self) -> list[Paper]:
        return list(self._db.scalars(select(Paper).order_by(Paper.created_at.desc())))

    def get(self, paper_id: uuid.UUID) -> Paper:
        paper = self._db.get(Paper, paper_id)
        if paper is None:
            raise NotFoundError("Paper not found.")
        return paper

    def file_path(self, paper: Paper) -> Path:
        path = (self._papers_dir / paper.file_path).resolve()
        if path.parent != self._papers_dir.resolve() or not path.is_file():
            raise NotFoundError("The PDF file for this paper is missing.")
        return path

    def latest_job(self, paper_id: uuid.UUID) -> IngestionJob:
        self.get(paper_id)
        job = self._db.scalar(
            select(IngestionJob)
            .where(IngestionJob.paper_id == paper_id)
            .order_by(IngestionJob.created_at.desc())
            .limit(1)
        )
        if job is None:
            raise NotFoundError("No ingestion job found for this paper.")
        return job

    def create_from_upload(self, upload: UploadFile) -> tuple[Paper, IngestionJob]:
        filename = sanitize_filename(upload.filename)
        incoming = self._papers_dir / ".incoming"
        incoming.mkdir(parents=True, exist_ok=True)
        temp_path = incoming / f"{uuid.uuid4()}.part"

        try:
            stored = stream_to_file(upload.file, temp_path, self._settings.max_upload_bytes)
            _, metadata_title = inspect_pdf(temp_path)

            existing = self._db.scalar(select(Paper.id).where(Paper.sha256 == stored.sha256))
            if existing is not None:
                raise ConflictError("This PDF is already in your library.", paper_id=str(existing))

            paper_id = uuid.uuid4()
            final_name = f"{paper_id}.pdf"
            os.replace(temp_path, self._papers_dir / final_name)
        finally:
            temp_path.unlink(missing_ok=True)

        paper = Paper(
            id=paper_id,
            title=metadata_title or Path(filename).stem,
            original_filename=filename,
            file_path=final_name,
            sha256=stored.sha256,
            file_size_bytes=stored.size_bytes,
            status=PaperStatus.QUEUED,
        )
        job = IngestionJob(paper_id=paper_id, status=JobStatus.QUEUED, attempt=1)
        self._db.add_all([paper, job])
        try:
            self._db.commit()
        except IntegrityError as exc:
            # Two uploads of the same file raced past the duplicate check.
            self._db.rollback()
            (self._papers_dir / final_name).unlink(missing_ok=True)
            raise ConflictError("This PDF is already in your library.") from exc
        except Exception:
            self._db.rollback()
            (self._papers_dir / final_name).unlink(missing_ok=True)
            raise
        return paper, job

    def retry(self, paper_id: uuid.UUID) -> tuple[Paper, IngestionJob | None]:
        paper = self.get(paper_id)
        if paper.status == PaperStatus.DELETING:
            self.delete(paper_id)
            return paper, None
        if paper.status != PaperStatus.FAILED:
            raise ConflictError(
                f"Only failed papers can be retried (current status: {paper.status})."
            )

        self._discard_partial_index(paper.id)
        last_attempt = self._db.scalar(
            select(IngestionJob.attempt)
            .where(IngestionJob.paper_id == paper.id)
            .order_by(IngestionJob.created_at.desc())
            .limit(1)
        )
        job = IngestionJob(
            paper_id=paper.id, status=JobStatus.QUEUED, attempt=(last_attempt or 0) + 1
        )
        paper.status = PaperStatus.QUEUED
        paper.error_message = None
        paper.chunk_count = 0
        self._db.add(job)
        self._db.commit()
        return paper, job

    def delete(self, paper_id: uuid.UUID) -> None:
        paper = self.get(paper_id)
        if paper.status in (PaperStatus.QUEUED, PaperStatus.PROCESSING):
            raise ConflictError("This paper is still being indexed. Delete it once indexing ends.")

        paper.status = PaperStatus.DELETING
        paper.error_message = None
        self._db.commit()
        # Drop it from sparse search right away; dense results are filtered by status.
        self._bm25.rebuild(self._db)

        try:
            self._vectors.delete_paper(paper.id)
            (self._papers_dir / paper.file_path).unlink(missing_ok=True)
            self._db.delete(paper)
            self._db.commit()
        except Exception as exc:
            self._db.rollback()
            logger.exception("Deletion of paper %s incomplete", paper_id)
            self._db.execute(
                update(Paper)
                .where(Paper.id == paper_id)
                .values(error_message="Deletion did not finish. Retry to remove it completely.")
            )
            self._db.commit()
            raise DependencyUnavailableError(
                "Deletion did not finish. The paper is hidden from search; retry the delete."
            ) from exc

    def _discard_partial_index(self, paper_id: uuid.UUID) -> None:
        self._vectors.delete_paper(paper_id)
        self._db.execute(delete(PaperChunk).where(PaperChunk.paper_id == paper_id))


def reconcile_interrupted_jobs(db: Session) -> int:
    """Jobs run in-process, so anything mid-flight at startup was lost with the old process."""
    now = datetime.now(UTC)
    jobs = db.execute(
        update(IngestionJob)
        .where(IngestionJob.status.in_([JobStatus.QUEUED, JobStatus.PROCESSING]))
        .values(status=JobStatus.FAILED, error_message=RESTART_MESSAGE, finished_at=now)
    ).rowcount
    db.execute(
        update(Paper)
        .where(Paper.status.in_([PaperStatus.QUEUED, PaperStatus.PROCESSING]))
        .values(status=PaperStatus.FAILED, error_message=RESTART_MESSAGE)
    )
    db.commit()
    if jobs:
        logger.warning("Marked %d interrupted ingestion job(s) as failed", jobs)
    return jobs
