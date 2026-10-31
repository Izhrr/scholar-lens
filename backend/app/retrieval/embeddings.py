import logging
from collections import OrderedDict
from threading import Lock
from typing import Protocol

from openai import OpenAI

from app.core.config import Settings
from app.core.errors import DependencyUnavailableError
from app.core.provider_errors import call_provider

logger = logging.getLogger(__name__)


class Embedder(Protocol):
    model_name: str

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class ApiEmbedder:
    """OpenAI-compatible /embeddings endpoint (OpenAI, Gemini...). Billed per token."""

    def __init__(self, settings: Settings) -> None:
        self.model_name = settings.resolved_embedding_model
        self._batch_size = settings.embedding_batch_size
        self._client = OpenAI(
            api_key=settings.resolved_embedding_api_key.get_secret_value() or None,
            base_url=settings.embedding_base_url or None,
            max_retries=settings.llm_max_retries,
            timeout=60,
        )

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self._batch_size):
            batch = texts[start : start + self._batch_size]
            response = call_provider(
                lambda batch=batch: self._client.embeddings.create(
                    model=self.model_name, input=batch
                ),
                provider="embedding",
            )
            vectors.extend(item.embedding for item in sorted(response.data, key=lambda d: d.index))
            tokens = response.usage.total_tokens if response.usage else 0
            logger.info("Embedded %d chunk(s), %d token(s)", len(batch), tokens)
        return vectors

    def embed_query(self, text: str) -> list[float]:
        response = call_provider(
            lambda: self._client.embeddings.create(model=self.model_name, input=[text]),
            provider="embedding",
        )
        return response.data[0].embedding


class LocalEmbedder:
    """Small ONNX model run in-process via fastembed. Free; downloads the model once."""

    def __init__(self, settings: Settings) -> None:
        self.model_name = settings.resolved_embedding_model
        self._batch_size = min(settings.embedding_batch_size, 64)
        self._cache_dir = settings.embedding_cache_dir
        self._model = None
        self._lock = Lock()

    def _load(self):
        if self._model is None:
            from fastembed import TextEmbedding  # heavy import, only when this provider is used

            logger.info("Loading local embedding model %s", self.model_name)
            try:
                self._model = TextEmbedding(self.model_name, cache_dir=str(self._cache_dir))
            except Exception as exc:
                logger.exception("Could not load embedding model %s", self.model_name)
                raise DependencyUnavailableError(
                    f"Local embedding model {self.model_name} could not be loaded. "
                    "Check the model name and that the first download can reach the internet."
                ) from exc
        return self._model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        with self._lock:
            model = self._load()
            return [v.tolist() for v in model.passage_embed(texts, batch_size=self._batch_size)]

    def embed_query(self, text: str) -> list[float]:
        with self._lock:
            return next(iter(self._load().query_embed([text]))).tolist()


class CachingEmbedder:
    """Remembers recent query vectors, so retries and repeated questions cost nothing."""

    def __init__(self, inner: Embedder, size: int = 256) -> None:
        self._inner = inner
        self.model_name = inner.model_name
        self._size = size
        self._cache: OrderedDict[str, list[float]] = OrderedDict()
        self._lock = Lock()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._inner.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        key = " ".join(text.lower().split())
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
        vector = self._inner.embed_query(text)
        with self._lock:
            self._cache[key] = vector
            if len(self._cache) > self._size:
                self._cache.popitem(last=False)
        return vector


def build_embedder(settings: Settings) -> Embedder:
    if settings.embedding_provider == "local":
        return CachingEmbedder(LocalEmbedder(settings))
    return CachingEmbedder(ApiEmbedder(settings))
