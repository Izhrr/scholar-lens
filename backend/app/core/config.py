from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


def _env(*names: str) -> AliasChoices:
    return AliasChoices(*names)


class Settings(BaseSettings):
    # Docker passes real env vars; local dev falls back to the repo-root .env.
    # Empty values (KEY=) count as unset, so optional settings can stay listed in .env.
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        extra="ignore",
        env_ignore_empty=True,
        populate_by_name=True,
    )

    # Chat model: any OpenAI-compatible API (OpenAI, DeepSeek, Gemini...).
    # The OPENAI_* names are accepted for .env files written before the rename.
    llm_api_key: SecretStr = Field(
        SecretStr(""), validation_alias=_env("LLM_API_KEY", "OPENAI_API_KEY")
    )
    llm_base_url: str | None = Field(None, validation_alias=_env("LLM_BASE_URL", "OPENAI_BASE_URL"))
    llm_model: str = Field("gpt-4.1-mini", validation_alias=_env("LLM_MODEL", "OPENAI_CHAT_MODEL"))
    llm_max_retries: int = Field(
        2, ge=0, le=10, validation_alias=_env("LLM_MAX_RETRIES", "OPENAI_MAX_RETRIES")
    )
    llm_max_output_tokens: int = Field(default=700, ge=64, le=8000)
    llm_temperature: float = Field(default=0.2, ge=0, le=1)
    # Only for reasoning models: e.g. "none" for DeepSeek, "minimal" for Gemini 3.
    llm_reasoning_effort: str | None = None
    # OpenAI reasoning models need max_completion_tokens; most other providers take max_tokens.
    llm_max_tokens_param: Literal["max_tokens", "max_completion_tokens"] = "max_tokens"

    # Embeddings: "api" calls an OpenAI-compatible /embeddings endpoint,
    # "local" runs a small ONNX model inside the backend (free, no network after download).
    embedding_provider: Literal["api", "local"] = "api"
    embedding_model: str | None = Field(
        None, validation_alias=_env("EMBEDDING_MODEL", "OPENAI_EMBEDDING_MODEL")
    )
    embedding_api_key: SecretStr | None = None
    embedding_base_url: str | None = None
    embedding_batch_size: int = Field(default=128, ge=1, le=2048)
    embedding_cache_dir: Path = Path("./data/models")

    # Compose sets DATABASE_URL; without it the URL is built from POSTGRES_* for local dev.
    database_url: str | None = None
    postgres_user: str = "scholarlens"
    postgres_password: SecretStr = SecretStr("change_me_local_only")
    postgres_db: str = "scholarlens"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    chroma_host: str = "localhost"
    # 8001 matches docker-compose.dev.yml; compose sets 8000 inside the network.
    chroma_port: int = 8001
    chroma_collection: str = "scholarlens_paper_chunks_v1"

    cors_origins: str = "http://localhost:3000"
    max_upload_mb: int = Field(default=25, ge=1, le=200)
    papers_dir: Path = Path("./data/papers")

    chunk_size: int = Field(default=800, ge=100)
    chunk_overlap: int = Field(default=120, ge=0)
    chunking_version: str = "recursive-v1"

    bm25_top_k: int = Field(default=12, ge=1)
    dense_top_k: int = Field(default=12, ge=1)
    rrf_k: int = Field(default=60, ge=1)
    final_top_k: int = Field(default=6, ge=1)
    max_context_chars: int = Field(default=15_000, ge=1_000)
    chat_history_turns: int = Field(default=4, ge=0, le=20)

    log_level: str = "INFO"

    @property
    def resolved_embedding_model(self) -> str:
        if self.embedding_model:
            return self.embedding_model
        return (
            "BAAI/bge-small-en-v1.5"
            if self.embedding_provider == "local"
            else ("text-embedding-3-small")
        )

    @property
    def resolved_embedding_api_key(self) -> SecretStr:
        if self.embedding_api_key and self.embedding_api_key.get_secret_value():
            return self.embedding_api_key
        return self.llm_api_key

    @property
    def sqlalchemy_url(self) -> str:
        if self.database_url:
            return self.database_url
        password = self.postgres_password.get_secret_value()
        return (
            f"postgresql+psycopg://{self.postgres_user}:{password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
