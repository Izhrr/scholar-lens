from app.core.config import Settings
from app.retrieval.embeddings import (
    ApiEmbedder,
    CachingEmbedder,
    LocalEmbedder,
    build_embedder,
)


class CountingEmbedder:
    model_name = "fake"

    def __init__(self) -> None:
        self.query_calls = 0

    def embed_documents(self, texts):
        return [[float(len(t))] for t in texts]

    def embed_query(self, text):
        self.query_calls += 1
        return [1.0]


def test_query_cache_ignores_case_and_whitespace():
    inner = CountingEmbedder()
    embedder = CachingEmbedder(inner)
    embedder.embed_query("What is RAG?")
    embedder.embed_query("  what   is rag? ")
    assert inner.query_calls == 1


def test_query_cache_evicts_oldest():
    inner = CountingEmbedder()
    embedder = CachingEmbedder(inner, size=1)
    embedder.embed_query("a")
    embedder.embed_query("b")
    embedder.embed_query("a")
    assert inner.query_calls == 3


def test_factory_picks_provider_and_default_model():
    local = build_embedder(Settings(_env_file=None, embedding_provider="local"))
    assert isinstance(local._inner, LocalEmbedder)
    assert local.model_name == "BAAI/bge-small-en-v1.5"

    api = build_embedder(Settings(_env_file=None, llm_api_key="k"))
    assert isinstance(api._inner, ApiEmbedder)
    assert api.model_name == "text-embedding-3-small"


def test_embedding_key_falls_back_to_llm_key():
    settings = Settings(_env_file=None, llm_api_key="shared")
    assert settings.resolved_embedding_api_key.get_secret_value() == "shared"
    settings = Settings(_env_file=None, llm_api_key="chat", embedding_api_key="embed")
    assert settings.resolved_embedding_api_key.get_secret_value() == "embed"
