import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings
from app.core.errors import ConflictError, NotFoundError, UnprocessableError
from app.db.models import (
    ChatMessage,
    ChatSession,
    MessageRole,
    MessageSource,
    Paper,
    PaperStatus,
)
from app.generation.citations import resolve_citations
from app.generation.llm import LLMClient
from app.generation.prompts import ABSTAIN_MESSAGE, build_messages
from app.retrieval.retriever import HybridRetriever
from app.schemas.chats import AskResponse, MessageOut, RetrievalStats, SourceOut

DEFAULT_TITLE = "New research chat"
_TITLE_LIMIT = 80


class ChatService:
    def __init__(
        self,
        db: Session,
        settings: Settings,
        retriever: HybridRetriever,
        llm: LLMClient,
    ) -> None:
        self._db = db
        self._settings = settings
        self._retriever = retriever
        self._llm = llm

    def create_session(self) -> ChatSession:
        session = ChatSession(title=DEFAULT_TITLE)
        self._db.add(session)
        self._db.commit()
        self._db.refresh(session)
        return session

    def list_sessions(self) -> list[ChatSession]:
        return list(self._db.scalars(select(ChatSession).order_by(ChatSession.updated_at.desc())))

    def list_messages(self, chat_id: uuid.UUID) -> list[MessageOut]:
        self._get_session(chat_id)
        messages = self._db.scalars(
            select(ChatMessage)
            .where(ChatMessage.session_id == chat_id)
            .options(selectinload(ChatMessage.sources))
            .order_by(ChatMessage.created_at, ChatMessage.id)
        )
        return [_message_out(message) for message in messages]

    def ask(
        self, chat_id: uuid.UUID, question: str, paper_ids: list[uuid.UUID] | None
    ) -> AskResponse:
        session = self._get_session(chat_id)
        self._validate_scope(paper_ids)

        retrieval = self._retriever.retrieve(self._db, question, paper_ids)
        chunks = retrieval.chunks
        history = self._recent_history(chat_id)

        model: str | None = None
        answer, cited_chunks = ABSTAIN_MESSAGE, {}
        grounded = False
        # No evidence means no LLM call: nothing to ground an answer in, and no cost.
        if chunks:
            completion = self._llm.complete(build_messages(question, chunks, history))
            model = completion.model
            cited = resolve_citations(completion.text, len(chunks))
            if not cited.abstained:
                answer = cited.text
                cited_chunks = {number: chunks[index] for number, index in cited.citations.items()}
                grounded = cited.grounded

        now = datetime.now(UTC)
        user_message = ChatMessage(
            session_id=chat_id, role=MessageRole.USER, content=question, created_at=now
        )
        # Explicit, strictly increasing timestamps keep question/answer order stable.
        assistant_message = ChatMessage(
            session_id=chat_id,
            role=MessageRole.ASSISTANT,
            content=answer,
            model=model,
            created_at=now + timedelta(microseconds=1),
        )
        assistant_message.sources = [
            MessageSource(
                chunk_id=chunk.chunk_id,
                paper_id=chunk.paper_id,
                citation_number=number,
                paper_title_snapshot=chunk.paper_title,
                page_number_snapshot=chunk.page_number,
                excerpt_snapshot=chunk.content,
                rrf_score=chunk.rrf_score,
            )
            for number, chunk in sorted(cited_chunks.items())
        ]
        if session.title == DEFAULT_TITLE and not history:
            session.title = _title_from(question)
        session.updated_at = now
        self._db.add_all([user_message, assistant_message])
        self._db.commit()

        return AskResponse(
            message_id=assistant_message.id,
            user_message_id=user_message.id,
            answer=answer,
            grounded=grounded,
            sources=[_source_out(source) for source in assistant_message.sources],
            retrieval=RetrievalStats(
                bm25_candidates=retrieval.bm25_candidates,
                dense_candidates=retrieval.dense_candidates,
                selected_chunks=len(chunks),
            ),
        )

    def _get_session(self, chat_id: uuid.UUID) -> ChatSession:
        session = self._db.get(ChatSession, chat_id)
        if session is None:
            raise NotFoundError("Chat not found.")
        return session

    def _validate_scope(self, paper_ids: list[uuid.UUID] | None) -> None:
        indexed = select(Paper.id).where(Paper.status == PaperStatus.INDEXED)
        if paper_ids is None:
            if not self._db.scalar(select(func.count()).select_from(indexed.subquery())):
                raise ConflictError(
                    "No indexed papers yet. Add a paper on the Knowledge page first."
                )
            return
        found = set(self._db.scalars(indexed.where(Paper.id.in_(paper_ids))))
        if len(found) != len(paper_ids):
            raise UnprocessableError(
                "Some selected papers are missing or not indexed. Refresh the scope and try again."
            )

    def _recent_history(self, chat_id: uuid.UUID) -> list[tuple[str, str]]:
        limit = self._settings.chat_history_turns * 2
        if limit == 0:
            return []
        rows = self._db.execute(
            select(ChatMessage.role, ChatMessage.content)
            .where(ChatMessage.session_id == chat_id)
            .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
            .limit(limit)
        ).all()
        return [(row.role.value, row.content) for row in reversed(rows)]


def _title_from(question: str) -> str:
    title = " ".join(question.split())
    if len(title) <= _TITLE_LIMIT:
        return title
    return title[: _TITLE_LIMIT - 1].rsplit(" ", 1)[0] + "…"


def _source_out(source: MessageSource) -> SourceOut:
    return SourceOut(
        citation_number=source.citation_number,
        chunk_id=source.chunk_id,
        paper_id=source.paper_id,
        paper_title=source.paper_title_snapshot,
        page_number=source.page_number_snapshot,
        excerpt=source.excerpt_snapshot,
        rrf_score=source.rrf_score,
    )


def _message_out(message: ChatMessage) -> MessageOut:
    return MessageOut(
        id=message.id,
        role=message.role,
        content=message.content,
        model=message.model,
        created_at=message.created_at,
        sources=[_source_out(source) for source in message.sources],
    )
