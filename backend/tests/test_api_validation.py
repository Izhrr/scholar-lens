import uuid

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_chat_service
from app.db.session import get_db
from app.main import create_app


class StubChatService:
    def ask(self, *_):  # pragma: no cover - validation must fail before this runs
        raise AssertionError("service should not be called")


@pytest.fixture
def client():
    app = create_app()
    app.dependency_overrides[get_chat_service] = StubChatService
    app.dependency_overrides[get_db] = lambda: None
    # No context manager: lifespan (DB, Chroma) is not started for validation tests.
    return TestClient(app)


@pytest.mark.parametrize(
    "body",
    [
        {"question": ""},
        {"question": "   "},
        {"question": "x" * 2001},
        {"question": "ok", "paper_ids": []},
        {"question": "ok", "paper_ids": ["not-a-uuid"]},
        {"question": "ok", "paper_ids": [str(uuid.uuid4()) for _ in range(21)]},
    ],
)
def test_ask_rejects_invalid_payloads(client, body):
    response = client.post(f"/api/chats/{uuid.uuid4()}/messages", json=body)
    assert response.status_code == 422


def test_unknown_route_ids_must_be_uuids(client):
    assert client.get("/api/chats/not-a-uuid/messages").status_code == 422


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}
