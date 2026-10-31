import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.db.models import MessageRole

MAX_SCOPE_PAPERS = 20


class ChatSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime


class ChatSessionList(BaseModel):
    items: list[ChatSessionOut]


class SourceOut(BaseModel):
    citation_number: int
    chunk_id: uuid.UUID | None
    paper_id: uuid.UUID | None
    paper_title: str
    page_number: int
    excerpt: str
    rrf_score: float | None


class MessageOut(BaseModel):
    id: uuid.UUID
    role: MessageRole
    content: str
    model: str | None
    created_at: datetime
    sources: list[SourceOut]


class MessageList(BaseModel):
    items: list[MessageOut]


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    paper_ids: list[uuid.UUID] | None = Field(
        default=None,
        description="null searches all indexed papers. An empty list is rejected.",
    )

    @field_validator("question")
    @classmethod
    def question_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Question cannot be empty.")
        return value

    @field_validator("paper_ids")
    @classmethod
    def scope_is_explicit(cls, value: list[uuid.UUID] | None) -> list[uuid.UUID] | None:
        if value is None:
            return None
        if not value:
            raise ValueError("Use null to search all papers, or select at least one paper.")
        unique = list(dict.fromkeys(value))
        if len(unique) > MAX_SCOPE_PAPERS:
            raise ValueError(f"Select at most {MAX_SCOPE_PAPERS} papers.")
        return unique


class RetrievalStats(BaseModel):
    bm25_candidates: int
    dense_candidates: int
    selected_chunks: int


class AskResponse(BaseModel):
    message_id: uuid.UUID
    user_message_id: uuid.UUID
    answer: str
    grounded: bool
    sources: list[SourceOut]
    retrieval: RetrievalStats
