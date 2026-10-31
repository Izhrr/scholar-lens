from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Docker passes real env vars; local dev falls back to the repo-root .env.
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    openai_api_key: SecretStr = SecretStr("")
    openai_chat_model: str = "gpt-4.1-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    llm_max_output_tokens: int = Field(default=700, ge=64, le=4000)
    llm_temperature: float = Field(default=0.2, ge=0, le=1)

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
    embedding_batch_size: int = Field(default=128, ge=1, le=2048)

    bm25_top_k: int = Field(default=12, ge=1)
    dense_top_k: int = Field(default=12, ge=1)
    rrf_k: int = Field(default=60, ge=1)
    final_top_k: int = Field(default=6, ge=1)
    max_context_chars: int = Field(default=15_000, ge=1_000)
    chat_history_turns: int = Field(default=4, ge=0, le=20)

    log_level: str = "INFO"

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
