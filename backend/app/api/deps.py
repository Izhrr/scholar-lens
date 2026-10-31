from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.services.chat_service import ChatService
from app.services.ingestion_service import IngestionService
from app.services.paper_service import PaperService

DbSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]


def get_paper_service(request: Request, db: DbSession, settings: AppSettings) -> PaperService:
    state = request.app.state
    return PaperService(db, settings, state.vector_store, state.bm25)


def get_ingestion_service(request: Request) -> IngestionService:
    return request.app.state.ingestion_service


def get_chat_service(request: Request, db: DbSession, settings: AppSettings) -> ChatService:
    state = request.app.state
    return ChatService(db, settings, state.retriever, state.llm)


PaperServiceDep = Annotated[PaperService, Depends(get_paper_service)]
IngestionServiceDep = Annotated[IngestionService, Depends(get_ingestion_service)]
ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]
