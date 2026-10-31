import asyncio
import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import chats, health, papers
from app.core.config import get_settings
from app.core.errors import AppError, app_error_handler
from app.core.logging import configure_logging
from app.db.session import SessionLocal
from app.generation.llm import LLMClient
from app.retrieval.bm25 import BM25Index
from app.retrieval.embeddings import build_embedder
from app.retrieval.retriever import HybridRetriever
from app.retrieval.vector_store import VectorStore
from app.services.ingestion_service import IngestionService
from app.services.paper_service import reconcile_interrupted_jobs

logger = logging.getLogger(__name__)


def _wait_for_vector_store(store: VectorStore, attempts: int = 15, delay: float = 2.0) -> None:
    for _ in range(attempts):
        if store.heartbeat():
            return
        time.sleep(delay)
    logger.warning("Chroma not reachable at startup; /api/ready will report it")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    settings.papers_dir.mkdir(parents=True, exist_ok=True)
    if not settings.llm_api_key.get_secret_value():
        logger.warning("LLM_API_KEY is empty: chat answers will fail")

    llm = LLMClient(settings)
    embedder = build_embedder(settings)
    vector_store = VectorStore(settings)
    bm25 = BM25Index()
    await asyncio.to_thread(_wait_for_vector_store, vector_store)

    with SessionLocal() as db:
        reconcile_interrupted_jobs(db)
        bm25.rebuild(db)

    app.state.llm = llm
    app.state.vector_store = vector_store
    app.state.bm25 = bm25
    app.state.retriever = HybridRetriever(settings, bm25, vector_store, embedder)
    app.state.ingestion_service = IngestionService(
        SessionLocal, settings, embedder, vector_store, bm25
    )
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="ScholarLens API",
        version="0.1.0",
        description="Upload academic PDFs and ask citation-grounded questions across them.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type"],
    )
    app.add_exception_handler(AppError, app_error_handler)
    app.include_router(health.router)
    app.include_router(papers.router)
    app.include_router(chats.router)
    return app


app = create_app()
