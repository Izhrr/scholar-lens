import logging
from collections.abc import Callable

import openai

from app.core.errors import DependencyUnavailableError

logger = logging.getLogger(__name__)


def call_provider[T](fn: Callable[[], T], provider: str) -> T:
    """Run an OpenAI-SDK call and turn provider failures into user-safe 503s."""
    try:
        return fn()
    except openai.AuthenticationError as exc:
        raise DependencyUnavailableError(
            f"The {provider} provider rejected the API key. Check the key in .env."
        ) from exc
    except openai.RateLimitError as exc:
        logger.warning("%s provider 429: code=%s", provider, exc.code)
        # OpenAI reports an empty balance as a 429 too; waiting does not fix that one.
        if exc.code == "insufficient_quota":
            raise _no_credit(provider) from exc
        raise DependencyUnavailableError(
            f"The {provider} provider's rate limit was reached. Wait a minute, then retry."
        ) from exc
    except openai.BadRequestError as exc:
        # Usually configuration: a wrong model name or an unsupported parameter.
        logger.warning("%s provider rejected the request: %s", provider, exc.message[:300])
        raise DependencyUnavailableError(
            f"The {provider} provider rejected the request: {exc.message[:200]}"
        ) from exc
    except openai.APIStatusError as exc:
        # DeepSeek signals an empty balance with 402 Payment Required.
        if exc.status_code == 402:
            raise _no_credit(provider) from exc
        logger.warning("%s provider returned HTTP %s", provider, exc.status_code)
        raise _unavailable(provider) from exc
    except openai.APIError as exc:
        logger.warning("%s provider request failed: %s", provider, type(exc).__name__)
        raise _unavailable(provider) from exc


def _no_credit(provider: str) -> DependencyUnavailableError:
    return DependencyUnavailableError(
        f"Your {provider} provider account has no credit left. Add credit, then retry."
    )


def _unavailable(provider: str) -> DependencyUnavailableError:
    return DependencyUnavailableError(f"The {provider} provider is unavailable. Try again.")
