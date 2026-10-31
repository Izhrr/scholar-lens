"""initial schema: papers, chunks, ingestion jobs, chats

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-10-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

paper_status = postgresql.ENUM(
    "queued", "processing", "indexed", "failed", "deleting", name="paper_status", create_type=False
)
job_status = postgresql.ENUM(
    "queued", "processing", "succeeded", "failed", name="job_status", create_type=False
)
message_role = postgresql.ENUM("user", "assistant", name="message_role", create_type=False)

UUID = postgresql.UUID(as_uuid=True)
uuid_pk = lambda: sa.Column(  # noqa: E731
    "id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
)
timestamp = lambda name: sa.Column(  # noqa: E731
    name, sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    bind = op.get_bind()
    paper_status.create(bind, checkfirst=True)
    job_status.create(bind, checkfirst=True)
    message_role.create(bind, checkfirst=True)

    op.create_table(
        "papers",
        uuid_pk(),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("original_filename", sa.Text, nullable=False),
        sa.Column("file_path", sa.Text, nullable=False, unique=True),
        sa.Column("sha256", sa.String(64), nullable=False, unique=True),
        sa.Column("mime_type", sa.Text, nullable=False, server_default="application/pdf"),
        sa.Column("file_size_bytes", sa.BigInteger, nullable=False),
        sa.Column("page_count", sa.Integer),
        sa.Column("chunk_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("status", paper_status, nullable=False, server_default="queued"),
        sa.Column("error_message", sa.Text),
        sa.Column("embedding_model", sa.Text),
        sa.Column("chunking_version", sa.Text),
        timestamp("created_at"),
        timestamp("updated_at"),
        sa.CheckConstraint("file_size_bytes > 0", name="ck_papers_file_size_positive"),
        sa.CheckConstraint("page_count >= 0", name="ck_papers_page_count_nonneg"),
        sa.CheckConstraint("chunk_count >= 0", name="ck_papers_chunk_count_nonneg"),
    )
    op.create_index("ix_papers_status", "papers", ["status"])
    op.create_index("ix_papers_created_at", "papers", [sa.text("created_at DESC")])

    op.create_table(
        "paper_chunks",
        uuid_pk(),
        sa.Column("paper_id", UUID, sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("page_number", sa.Integer, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("char_start", sa.Integer),
        sa.Column("char_end", sa.Integer),
        sa.Column("token_count", sa.Integer),
        timestamp("created_at"),
        sa.UniqueConstraint("paper_id", "chunk_index", name="uq_chunks_paper_chunk_index"),
        sa.CheckConstraint("chunk_index >= 0", name="ck_chunks_chunk_index_nonneg"),
        sa.CheckConstraint("page_number >= 1", name="ck_chunks_page_number_positive"),
        sa.CheckConstraint(
            "char_start IS NULL OR char_start >= 0", name="ck_chunks_char_start_nonneg"
        ),
        sa.CheckConstraint(
            "char_end IS NULL OR char_start IS NULL OR char_end >= char_start",
            name="ck_chunks_char_range",
        ),
    )
    op.create_index("ix_chunks_paper_id", "paper_chunks", ["paper_id"])

    op.create_table(
        "ingestion_jobs",
        uuid_pk(),
        sa.Column("paper_id", UUID, sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", job_status, nullable=False, server_default="queued"),
        sa.Column("attempt", sa.Integer, nullable=False, server_default="1"),
        sa.Column("error_message", sa.Text),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        timestamp("created_at"),
        sa.CheckConstraint("attempt >= 1", name="ck_jobs_attempt_positive"),
    )
    op.create_index(
        "ix_jobs_paper_created", "ingestion_jobs", ["paper_id", sa.text("created_at DESC")]
    )

    op.create_table(
        "chat_sessions",
        uuid_pk(),
        sa.Column("title", sa.Text, nullable=False, server_default="New research chat"),
        timestamp("created_at"),
        timestamp("updated_at"),
    )

    op.create_table(
        "chat_messages",
        uuid_pk(),
        sa.Column(
            "session_id",
            UUID,
            sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", message_role, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("model", sa.Text),
        timestamp("created_at"),
    )
    op.create_index(
        "ix_messages_session_created", "chat_messages", ["session_id", "created_at", "id"]
    )

    op.create_table(
        "message_sources",
        uuid_pk(),
        sa.Column(
            "message_id",
            UUID,
            sa.ForeignKey("chat_messages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_id", UUID, sa.ForeignKey("paper_chunks.id", ondelete="SET NULL")),
        sa.Column("paper_id", UUID, sa.ForeignKey("papers.id", ondelete="SET NULL")),
        sa.Column("citation_number", sa.Integer, nullable=False),
        sa.Column("paper_title_snapshot", sa.Text, nullable=False),
        sa.Column("page_number_snapshot", sa.Integer, nullable=False),
        sa.Column("excerpt_snapshot", sa.Text, nullable=False),
        sa.Column("rrf_score", sa.Float),
        sa.UniqueConstraint("message_id", "citation_number", name="uq_sources_message_citation"),
        sa.CheckConstraint("citation_number > 0", name="ck_sources_citation_positive"),
    )


def downgrade() -> None:
    op.drop_table("message_sources")
    op.drop_index("ix_messages_session_created", table_name="chat_messages")
    op.drop_table("chat_messages")
    op.drop_table("chat_sessions")
    op.drop_index("ix_jobs_paper_created", table_name="ingestion_jobs")
    op.drop_table("ingestion_jobs")
    op.drop_index("ix_chunks_paper_id", table_name="paper_chunks")
    op.drop_table("paper_chunks")
    op.drop_index("ix_papers_created_at", table_name="papers")
    op.drop_index("ix_papers_status", table_name="papers")
    op.drop_table("papers")
    message_role.drop(op.get_bind(), checkfirst=True)
    job_status.drop(op.get_bind(), checkfirst=True)
    paper_status.drop(op.get_bind(), checkfirst=True)
