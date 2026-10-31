import logging
from dataclasses import dataclass

from openai import OpenAI

from app.core.config import Settings
from app.core.errors import DependencyUnavailableError
from app.core.provider_errors import call_provider

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Completion:
    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int


class LLMClient:
    """Chat completions over any OpenAI-compatible API. The only per-question paid call."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = OpenAI(
            api_key=settings.llm_api_key.get_secret_value() or None,
            base_url=settings.llm_base_url or None,
            max_retries=settings.llm_max_retries,
            timeout=60,
        )

    @property
    def model(self) -> str:
        return self._settings.llm_model

    def complete(self, messages: list[dict[str, str]]) -> Completion:
        s = self._settings
        options: dict[str, object] = {s.llm_max_tokens_param: s.llm_max_output_tokens}
        if s.llm_reasoning_effort:
            options["reasoning_effort"] = s.llm_reasoning_effort
        response = call_provider(
            lambda: self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=s.llm_temperature,
                **options,
            ),
            provider="chat",
        )

        choice = response.choices[0]
        text = (choice.message.content or "").strip()
        if choice.finish_reason == "length":
            logger.warning("Completion hit LLM_MAX_OUTPUT_TOKENS (%s)", self.model)
            # Reasoning models can spend the whole budget thinking and return nothing.
            if not text:
                raise DependencyUnavailableError(
                    "The model used its whole output budget before answering. "
                    "Raise LLM_MAX_OUTPUT_TOKENS or lower LLM_REASONING_EFFORT."
                )

        usage = response.usage
        completion = Completion(
            text=text,
            model=response.model,
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
        )
        logger.info(
            "Chat completion %s: %d prompt + %d completion tokens",
            completion.model,
            completion.prompt_tokens,
            completion.completion_tokens,
        )
        return completion
