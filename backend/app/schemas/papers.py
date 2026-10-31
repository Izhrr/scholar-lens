import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.db.models import JobStatus, PaperStatus


class PaperOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    original_filename: str
    file_size_bytes: int
    page_count: int | None
    chunk_count: int
    status: PaperStatus
    error_message: str | None
    embedding_model: str | None
    created_at: datetime
    updated_at: datetime


class PaperList(BaseModel):
    items: list[PaperOut]


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    paper_id: uuid.UUID
    status: JobStatus
    attempt: int
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime


class UploadAccepted(BaseModel):
    paper_id: uuid.UUID
    job_id: uuid.UUID | None
    status: PaperStatus
