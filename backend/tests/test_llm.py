from types import SimpleNamespace

import httpx
import openai
import pytest

from app.core.config import Settings
from app.core.errors import DependencyUnavailableError
from app.core.provider_errors import call_provider
from app.generation.llm import LLMClient


class FakeCompletions:
    def __init__(self, content: str | None, finish_reason: str = "stop") -> None:
        self.content = content
        self.finish_reason = finish_reason
        self.kwargs: dict = {}

    def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(
            model=kwargs["model"],
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=self.content),
                    finish_reason=self.finish_reason,
                )
            ],
            usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
        )


def client(completions: FakeCompletions, **overrides) -> LLMClient:
    llm = LLMClient(Settings(_env_file=None, llm_api_key="test", **overrides))
    llm._client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    return llm


MESSAGES = [{"role": "user", "content": "q"}]


def test_defaults_send_max_tokens_and_no_reasoning_effort():
    fake = FakeCompletions("Answer [S1].")
    client(fake).complete(MESSAGES)
    assert fake.kwargs["max_tokens"] == 700
    assert "max_completion_tokens" not in fake.kwargs
    assert "reasoning_effort" not in fake.kwargs


def test_reasoning_effort_and_token_param_are_configurable():
    fake = FakeCompletions("Answer [S1].")
    client(
        fake, llm_reasoning_effort="none", llm_max_tokens_param="max_completion_tokens"
    ).complete(MESSAGES)
    assert fake.kwargs["reasoning_effort"] == "none"
    assert fake.kwargs["max_completion_tokens"] == 700


def test_empty_truncated_completion_raises_instead_of_abstaining():
    with pytest.raises(DependencyUnavailableError, match="LLM_MAX_OUTPUT_TOKENS"):
        client(FakeCompletions(None, "length")).complete(MESSAGES)


def test_partial_truncated_completion_is_kept():
    assert client(FakeCompletions("Partial [S1]", "length")).complete(MESSAGES).text == (
        "Partial [S1]"
    )


def _status_error(status: int, body: dict) -> openai.APIStatusError:
    request = httpx.Request("POST", "https://api.example.com/v1/chat/completions")
    response = httpx.Response(status, request=request, json=body)
    return openai.OpenAI(api_key="x")._make_status_error_from_response(response)


@pytest.mark.parametrize(
    ("status", "body", "expected"),
    [
        (402, {"error": {"message": "Insufficient Balance"}}, "no credit left"),
        (429, {"error": {"code": "insufficient_quota", "message": "quota"}}, "no credit left"),
        (429, {"error": {"code": "rate_limit_exceeded", "message": "slow"}}, "rate limit"),
        (401, {"error": {"message": "bad key"}}, "rejected the API key"),
        (400, {"error": {"message": "Model Not Exist"}}, "Model Not Exist"),
        (500, {"error": {"message": "boom"}}, "unavailable"),
    ],
)
def test_provider_errors_map_to_clear_messages(status, body, expected):
    error = _status_error(status, body)

    def fail():
        raise error

    with pytest.raises(DependencyUnavailableError, match=expected):
        call_provider(fail, provider="chat")
