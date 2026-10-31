import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class PaperStatus(enum.StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"
    DELETING = "deleting"


class JobStatus(enum.StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class MessageRole(enum.StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


def _pg_enum(enum_cls: type[enum.Enum], name: str) -> Enum:
    return Enum(enum_cls, name=name, values_callable=lambda e: [m.value for m in e])


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def _created_at() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Paper(Base):
    __tablename__ = "papers"
    __table_args__ = (
        CheckConstraint("file_size_bytes > 0", name="ck_papers_file_size_positive"),
        CheckConstraint("page_count >= 0", name="ck_papers_page_count_nonneg"),
        CheckConstraint("chunk_count >= 0", name="ck_papers_chunk_count_nonneg"),
        Index("ix_papers_status", "status"),
        Index("ix_papers_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    title: Mapped[str] = mapped_column(Text, nullable=False)
    original_filename: Mapped[str] = mapped_column(Text, nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    mime_type: Mapped[str] = mapped_column(Text, nullable=False, server_default="application/pdf")
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    page_count: Mapped[int | None] = mapped_column(Integer)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    status: Mapped[PaperStatus] = mapped_column(
        _pg_enum(PaperStatus, "paper_status"), nullable=False, default=PaperStatus.QUEUED
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    embedding_model: Mapped[str | None] = mapped_column(Text)
    chunking_version: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    chunks: Mapped[list["PaperChunk"]] = relationship(
        back_populates="paper", cascade="all, delete-orphan", passive_deletes=True
    )
    jobs: Mapped[list["IngestionJob"]] = relationship(
        back_populates="paper", cascade="all, delete-orphan", passive_deletes=True
    )


class PaperChunk(Base):
    __tablename__ = "paper_chunks"
    __table_args__ = (
        UniqueConstraint("paper_id", "chunk_index", name="uq_chunks_paper_chunk_index"),
        CheckConstraint("chunk_index >= 0", name="ck_chunks_chunk_index_nonneg"),
        CheckConstraint("page_number >= 1", name="ck_chunks_page_number_positive"),
        CheckConstraint(
            "char_start IS NULL OR char_start >= 0", name="ck_chunks_char_start_nonneg"
        ),
        CheckConstraint(
            "char_end IS NULL OR char_start IS NULL OR char_end >= char_start",
            name="ck_chunks_char_range",
        ),
        Index("ix_chunks_paper_id", "paper_id"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    paper_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("papers.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    char_start: Mapped[int | None] = mapped_column(Integer)
    char_end: Mapped[int | None] = mapped_column(Integer)
    token_count: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = _created_at()

    paper: Mapped[Paper] = relationship(back_populates="chunks")


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"
    __table_args__ = (
        CheckConstraint("attempt >= 1", name="ck_jobs_attempt_positive"),
        Index("ix_jobs_paper_created", "paper_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    paper_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("papers.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[JobStatus] = mapped_column(
        _pg_enum(JobStatus, "job_status"), nullable=False, default=JobStatus.QUEUED
    )
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _created_at()

    paper: Mapped[Paper] = relationship(back_populates="jobs")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[uuid.UUID] = _uuid_pk()
    title: Mapped[str] = mapped_column(Text, nullable=False, server_default="New research chat")
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="(ChatMessage.created_at, ChatMessage.id)",
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (Index("ix_messages_session_created", "session_id", "created_at", "id"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[MessageRole] = mapped_column(_pg_enum(MessageRole, "message_role"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _created_at()

    session: Mapped[ChatSession] = relationship(back_populates="messages")
    sources: Mapped[list["MessageSource"]] = relationship(
        back_populates="message",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="MessageSource.citation_number",
    )


class MessageSource(Base):
    __tablename__ = "message_sources"
    __table_args__ = (
        UniqueConstraint("message_id", "citation_number", name="uq_sources_message_citation"),
        CheckConstraint("citation_number > 0", name="ck_sources_citation_positive"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=False
    )
    # Snapshots keep chat history readable after the cited paper is deleted.
    chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("paper_chunks.id", ondelete="SET NULL")
    )
    paper_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("papers.id", ondelete="SET NULL")
    )
    citation_number: Mapped[int] = mapped_column(Integer, nullable=False)
    paper_title_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    page_number_snapshot: Mapped[int] = mapped_column(Integer, nullable=False)
    excerpt_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    rrf_score: Mapped[float | None] = mapped_column(Float)

    message: Mapped[ChatMessage] = relationship(back_populates="sources")
