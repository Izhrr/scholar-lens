import uuid

from fastapi import APIRouter, status

from app.api.deps import ChatServiceDep
from app.schemas.chats import (
    AskRequest,
    AskResponse,
    ChatSessionList,
    ChatSessionOut,
    MessageList,
)

router = APIRouter(prefix="/api/chats", tags=["chats"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ChatSessionOut)
def create_chat(chats: ChatServiceDep) -> ChatSessionOut:
    return ChatSessionOut.model_validate(chats.create_session())


@router.get("", response_model=ChatSessionList)
def list_chats(chats: ChatServiceDep) -> ChatSessionList:
    return ChatSessionList(items=[ChatSessionOut.model_validate(s) for s in chats.list_sessions()])


@router.get("/{chat_id}/messages", response_model=MessageList)
def list_messages(chat_id: uuid.UUID, chats: ChatServiceDep) -> MessageList:
    return MessageList(items=chats.list_messages(chat_id))


@router.post("/{chat_id}/messages", response_model=AskResponse)
def ask(chat_id: uuid.UUID, body: AskRequest, chats: ChatServiceDep) -> AskResponse:
    return chats.ask(chat_id, body.question, body.paper_ids)
