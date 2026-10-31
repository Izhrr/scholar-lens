import logging
from collections import OrderedDict
from dataclasses import dataclass
from threading import Lock

import openai
from openai import OpenAI

from app.core.config import Settings
from app.core.errors import DependencyUnavailableError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Completion:
    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int


class OpenAIGateway:
    """Single entry point for paid OpenAI calls, so cost controls live in one place."""

    def __init__(self, settings: Settings, query_cache_size: int = 256) -> None:
        self._settings = settings
        self._client = OpenAI(
            api_key=settings.openai_api_key.get_secret_value() or None,
            max_retries=2,
            timeout=60,
        )
        self._query_cache: OrderedDict[str, list[float]] = OrderedDict()
        self._query_cache_size = query_cache_size
        self._cache_lock = Lock()

    @property
    def embedding_model(self) -> str:
        return self._settings.openai_embedding_model

    @property
    def chat_model(self) -> str:
        return self._settings.openai_chat_model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        batch_size = self._settings.embedding_batch_size
        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            response = self._call(
                lambda batch=batch: self._client.embeddings.create(
                    model=self.embedding_model, input=batch
                )
            )
            vectors.extend(item.embedding for item in sorted(response.data, key=lambda d: d.index))
            logger.info(
                "Embedded %d chunk(s), %d token(s)", len(batch), response.usage.total_tokens
            )
        return vectors

    def embed_query(self, text: str) -> list[float]:
        # Repeated questions (retries, follow-ups) reuse the vector instead of paying again.
        key = " ".join(text.lower().split())
        with self._cache_lock:
            if key in self._query_cache:
                self._query_cache.move_to_end(key)
                return self._query_cache[key]

        response = self._call(
            lambda: self._client.embeddings.create(model=self.embedding_model, input=[text])
        )
        vector = response.data[0].embedding
        with self._cache_lock:
            self._query_cache[key] = vector
            if len(self._query_cache) > self._query_cache_size:
                self._query_cache.popitem(last=False)
        return vector

    def complete(self, messages: list[dict[str, str]]) -> Completion:
        response = self._call(
            lambda: self._client.chat.completions.create(
                model=self.chat_model,
                messages=messages,
                temperature=self._settings.llm_temperature,
                max_completion_tokens=self._settings.llm_max_output_tokens,
            )
        )
        usage = response.usage
        completion = Completion(
            text=(response.choices[0].message.content or "").strip(),
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

    @staticmethod
    def _call(fn):
        try:
            return fn()
        except openai.AuthenticationError as exc:
            raise DependencyUnavailableError(
                "OpenAI rejected the API key. Check OPENAI_API_KEY in .env."
            ) from exc
        except openai.RateLimitError as exc:
            raise DependencyUnavailableError(
                "OpenAI rate limit or quota reached. Wait a moment or check your billing."
            ) from exc
        except openai.APIError as exc:
            logger.warning("OpenAI request failed: %s", type(exc).__name__)
            raise DependencyUnavailableError("OpenAI is unavailable right now. Try again.") from exc
