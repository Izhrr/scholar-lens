import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import Paper, PaperChunk, PaperStatus
from app.retrieval.bm25 import BM25Index
from app.retrieval.embeddings import Embedder
from app.retrieval.fusion import reciprocal_rank_fusion
from app.retrieval.vector_store import VectorStore


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: uuid.UUID
    paper_id: uuid.UUID
    paper_title: str
    page_number: int
    content: str
    rrf_score: float


@dataclass(frozen=True)
class RetrievalResult:
    chunks: list[RetrievedChunk]
    bm25_candidates: int
    dense_candidates: int


class HybridRetriever:
    def __init__(
        self,
        settings: Settings,
        bm25: BM25Index,
        vector_store: VectorStore,
        embedder: Embedder,
    ) -> None:
        self._settings = settings
        self._bm25 = bm25
        self._vectors = vector_store
        self._embedder = embedder

    def retrieve(
        self, db: Session, query: str, paper_ids: list[uuid.UUID] | None
    ) -> RetrievalResult:
        s = self._settings
        sparse = self._bm25.search(query, s.bm25_top_k, paper_ids)
        dense = self._vectors.query(self._embedder.embed_query(query), s.dense_top_k, paper_ids)
        fused = reciprocal_rank_fusion([sparse, dense], k=s.rrf_k)

        rows = self._load_indexed_chunks(db, [chunk_id for chunk_id, _ in fused])
        selected: list[RetrievedChunk] = []
        budget = s.max_context_chars
        for chunk_id, score in fused:
            row = rows.get(chunk_id)
            # Rows missing here belong to papers being deleted or re-ingested: skip them.
            if row is None:
                continue
            content = row.content
            if len(content) > budget:
                if selected:
                    break
                content = content[:budget]
            selected.append(
                RetrievedChunk(
                    chunk_id=chunk_id,
                    paper_id=row.paper_id,
                    paper_title=row.title,
                    page_number=row.page_number,
                    content=content,
                    rrf_score=score,
                )
            )
            budget -= len(content)
            if len(selected) >= s.final_top_k or budget <= 0:
                break

        return RetrievalResult(
            chunks=selected, bm25_candidates=len(sparse), dense_candidates=len(dense)
        )

    @staticmethod
    def _load_indexed_chunks(db: Session, chunk_ids: list[uuid.UUID]) -> dict:
        if not chunk_ids:
            return {}
        rows = db.execute(
            select(
                PaperChunk.id,
                PaperChunk.paper_id,
                PaperChunk.page_number,
                PaperChunk.content,
                Paper.title,
            )
            .join(Paper, Paper.id == PaperChunk.paper_id)
            .where(PaperChunk.id.in_(chunk_ids), Paper.status == PaperStatus.INDEXED)
        ).all()
        return {row.id: row for row in rows}
