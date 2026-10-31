import logging
import uuid
from dataclasses import dataclass
from threading import Lock

import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection

from app.core.config import Settings
from app.core.errors import DependencyUnavailableError

logger = logging.getLogger(__name__)

_UPSERT_BATCH = 256


@dataclass(frozen=True)
class ChunkVector:
    chunk_id: uuid.UUID
    paper_id: uuid.UUID
    page_number: int
    chunk_index: int
    content: str
    embedding: list[float]


class VectorStore:
    """Chroma wrapper. IDs are PostgreSQL chunk UUIDs, so both stores reconcile by ID."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: ClientAPI | None = None
        self._collection: Collection | None = None
        self._lock = Lock()

    @property
    def collection(self) -> Collection:
        if self._collection is None:
            with self._lock:
                if self._collection is None:
                    try:
                        self._client = chromadb.HttpClient(
                            host=self._settings.chroma_host, port=self._settings.chroma_port
                        )
                        self._collection = self._client.get_or_create_collection(
                            name=self._settings.chroma_collection,
                            configuration={"hnsw": {"space": "cosine"}},
                            embedding_function=None,
                        )
                    except Exception as exc:
                        raise DependencyUnavailableError("Vector store is unavailable.") from exc
        return self._collection

    def heartbeat(self) -> bool:
        try:
            _ = self.collection
            self._client.heartbeat()
            return True
        except Exception:
            return False

    def upsert(self, vectors: list[ChunkVector], embedding_model: str) -> None:
        for start in range(0, len(vectors), _UPSERT_BATCH):
            batch = vectors[start : start + _UPSERT_BATCH]
            self.collection.upsert(
                ids=[str(v.chunk_id) for v in batch],
                embeddings=[v.embedding for v in batch],
                documents=[v.content for v in batch],
                metadatas=[
                    {
                        "paper_id": str(v.paper_id),
                        "page_number": v.page_number,
                        "chunk_index": v.chunk_index,
                        "embedding_model": embedding_model,
                    }
                    for v in batch
                ],
            )

    def count_for_paper(self, paper_id: uuid.UUID) -> int:
        result = self.collection.get(where={"paper_id": str(paper_id)}, include=[])
        return len(result["ids"])

    def delete_paper(self, paper_id: uuid.UUID) -> None:
        self.collection.delete(where={"paper_id": str(paper_id)})

    def query(
        self, embedding: list[float], top_k: int, paper_ids: list[uuid.UUID] | None
    ) -> list[uuid.UUID]:
        where = None
        if paper_ids:
            ids = [str(pid) for pid in paper_ids]
            where = {"paper_id": ids[0]} if len(ids) == 1 else {"paper_id": {"$in": ids}}
        try:
            result = self.collection.query(
                query_embeddings=[embedding], n_results=top_k, where=where, include=[]
            )
        except DependencyUnavailableError:
            raise
        except Exception as exc:
            logger.warning("Chroma query failed: %s", type(exc).__name__)
            raise DependencyUnavailableError("Vector store query failed.") from exc
        return [uuid.UUID(chunk_id) for chunk_id in result["ids"][0]]
