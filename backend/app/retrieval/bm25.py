import logging
import re
import uuid
from dataclasses import dataclass
from threading import RLock

from rank_bm25 import BM25Okapi
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Paper, PaperChunk, PaperStatus

logger = logging.getLogger(__name__)

_TOKEN = re.compile(r"\w+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


@dataclass(frozen=True)
class _Entry:
    chunk_id: uuid.UUID
    paper_id: uuid.UUID


class BM25Index:
    """In-memory sparse index over chunks of indexed papers.

    Safe only with a single backend worker: each process would hold its own copy.
    """

    def __init__(self) -> None:
        self._lock = RLock()
        self._bm25: BM25Okapi | None = None
        self._entries: list[_Entry] = []

    @property
    def size(self) -> int:
        return len(self._entries)

    def rebuild(self, db: Session) -> None:
        rows = db.execute(
            select(PaperChunk.id, PaperChunk.paper_id, PaperChunk.content)
            .join(Paper, Paper.id == PaperChunk.paper_id)
            .where(Paper.status == PaperStatus.INDEXED)
            .order_by(PaperChunk.paper_id, PaperChunk.chunk_index)
        ).all()
        self.build([(r.id, r.paper_id, r.content) for r in rows])
        logger.info("BM25 index rebuilt with %d chunk(s)", len(rows))

    def build(self, rows: list[tuple[uuid.UUID, uuid.UUID, str]]) -> None:
        entries = [_Entry(chunk_id, paper_id) for chunk_id, paper_id, _ in rows]
        corpus = [tokenize(content) for _, _, content in rows]
        bm25 = BM25Okapi(corpus) if corpus else None
        with self._lock:
            self._entries = entries
            self._bm25 = bm25

    def search(
        self, query: str, top_k: int, paper_ids: list[uuid.UUID] | None = None
    ) -> list[uuid.UUID]:
        tokens = tokenize(query)
        with self._lock:
            if self._bm25 is None or not tokens:
                return []
            scores = self._bm25.get_scores(tokens)
            allowed = set(paper_ids) if paper_ids else None
            ranked = [
                (score, i)
                for i, score in enumerate(scores)
                if score > 0 and (allowed is None or self._entries[i].paper_id in allowed)
            ]
            # Ties broken by corpus position, so results are deterministic.
            ranked.sort(key=lambda pair: (-pair[0], pair[1]))
            return [self._entries[i].chunk_id for _, i in ranked[:top_k]]
