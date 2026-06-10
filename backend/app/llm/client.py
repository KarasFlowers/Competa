from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)

# Mock mode flag
_is_mock = False


class LLMContentFilterError(RuntimeError):
    """Raised when the provider blocks a request for safety or policy reasons."""


def is_mock_mode() -> bool:
    """Check if mock LLM mode is enabled."""
    return _is_mock


def set_mock_mode(enabled: bool) -> None:
    """Enable or disable mock LLM mode."""
    global _is_mock
    _is_mock = enabled


@dataclass
class LLMResponse:
    content: str
    input_tokens: int
    output_tokens: int
    model: str
    duration: float


# ---------------------------------------------------------------------------
# Multi-key client pool — one AsyncOpenAI per API key
# ---------------------------------------------------------------------------

_clients: list[AsyncOpenAI] = []
_current_key_index: int = 0


def _init_clients() -> None:
    """Build a client for each configured API key."""
    global _clients
    if _clients:
        return
    keys = settings.llm_api_keys
    if not keys:
        # Fallback: single client with whatever LLM_API_KEY has (may be empty)
        _clients = [AsyncOpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL or None,
        )]
    else:
        _clients = [
            AsyncOpenAI(api_key=k, base_url=settings.LLM_BASE_URL or None)
            for k in keys
        ]


def _get_client() -> AsyncOpenAI:
    """Return the current active client."""
    _init_clients()
    return _clients[_current_key_index % len(_clients)]


def _rotate_client() -> AsyncOpenAI | None:
    """Switch to the next API key. Returns new client or None if exhausted."""
    global _current_key_index
    _init_clients()
    if len(_clients) <= 1:
        return None
    _current_key_index = (_current_key_index + 1) % len(_clients)
    logger.info("Rotated to API key index %d", _current_key_index)
    return _clients[_current_key_index]


def _is_retryable_auth_error(exc: Exception) -> bool:
    """Check if the error is likely a rate-limit / key-invalid issue worth retrying with another key."""
    status = getattr(exc, "status_code", None)
    if status in (401, 403, 429):
        return True
    msg = str(exc).lower()
    if any(kw in msg for kw in ("rate_limit", "quota", "invalid api key", "authentication", "permission")):
        return True
    return False


def _is_content_filter_error(exc: Exception) -> bool:
    """Check if the error is a content filter / safety refusal from the LLM provider.

    Common indicators:
    - OpenAI: content_policy_violation, content_filter
    - Zhipu/GLM: 1301 error code, contentFilter
    - Generic: "content filter", "safety", "inappropriate content"
    """
    status = getattr(exc, "status_code", None)
    # Zhipu/GLM uses 1301 for content filter
    if status == 1301:
        return True
    msg_parts = [str(exc)]
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        inner = body.get("error", {})
        if isinstance(inner, dict):
            for field in ("message", "type", "code"):
                value = inner.get(field)
                if value:
                    msg_parts.append(str(value))

    msg = " ".join(msg_parts).lower()
    if any(kw in msg for kw in (
        "content_filter", "contentfilter", "content policy",
        "safety", "inappropriate content", "flagged",
        "content_policy_violation",
        "your request was blocked",
        "request was blocked",
        "blocked by policy",
        "policy_violation",
    )):
        return True
    # Check OpenAI-style error structure
    if isinstance(body, dict):
        inner = body.get("error", {})
        if isinstance(inner, dict) and inner.get("code") in (
            "content_filter", "content_policy_violation",
        ):
            return True
    return False


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token for mixed CJK/English."""
    return max(1, len(text) // 4)


async def call_llm(
    messages: list[dict[str, str]],
    model: str | None = None,
    json_mode: bool = True,
    max_tokens: int = 4096,
    temperature: float = 0.2,
    token_budget: int = 8000,
) -> LLMResponse:
    """Call LLM via OpenAI-compatible API with multi-key fallback.

    Args:
        messages: Chat messages (system + user).
        model: Model name override; defaults to settings.LLM_MODEL.
        json_mode: If True, request JSON output format.
        max_tokens: Max output tokens.
        temperature: Sampling temperature.
        token_budget: Max input token estimate; truncates user message if exceeded.

    Returns:
        LLMResponse with content and usage stats.
    """
    # Route to mock if enabled
    if settings.LLM_MOCK or _is_mock:
        from app.llm.mock_client import call_mock_llm
        return await call_mock_llm(messages)

    model = model or settings.LLM_MODEL or "gpt-4o-mini"

    # Token budget enforcement: truncate the last user message if too long
    total_estimate = sum(estimate_tokens(m.get("content", "")) for m in messages)
    if total_estimate > token_budget and len(messages) > 1:
        excess = total_estimate - token_budget
        chars_to_trim = excess * 4
        last_msg = messages[-1]
        if last_msg["role"] == "user" and len(last_msg["content"]) > chars_to_trim:
            messages = messages[:]  # shallow copy
            messages[-1] = {
                **last_msg,
                "content": last_msg["content"][: -chars_to_trim]
                + "\n\n[Content truncated due to token budget]",
            }

    kwargs: dict = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    # Try each available API key on auth/rate-limit errors
    _init_clients()
    tried_keys = 0
    content_filter_retried = False
    while tried_keys < len(_clients):
        client = _clients[_current_key_index % len(_clients)]
        try:
            start = time.monotonic()
            response = await client.chat.completions.create(**kwargs)
            duration = time.monotonic() - start

            choice = response.choices[0]
            usage = response.usage

            return LLMResponse(
                content=choice.message.content or "",
                input_tokens=usage.prompt_tokens if usage else 0,
                output_tokens=usage.completion_tokens if usage else 0,
                model=response.model,
                duration=round(duration, 3),
            )
        except Exception as exc:
            # Content filter: truncate long messages and retry once
            if _is_content_filter_error(exc):
                if not content_filter_retried:
                    logger.warning(
                        "LLM content filter triggered, truncating messages and retrying"
                    )
                    content_filter_retried = True
                    # Truncate the last user message to reduce trigger risk
                    msgs = kwargs.get("messages", messages)
                    if len(msgs) > 1 and msgs[-1]["role"] == "user":
                        original = msgs[-1]["content"]
                        if len(original) > 400:
                            truncated = (
                                original[:400]
                                + "\n\n[Content truncated for safety]"
                            )
                            kwargs["messages"] = (
                                msgs[:-1]
                                + [{**msgs[-1], "content": truncated}]
                            )
                    continue
                raise LLMContentFilterError(str(exc)) from exc

            # Auth/rate-limit: rotate to next API key
            if _is_retryable_auth_error(exc) and tried_keys < len(_clients) - 1:
                logger.warning(
                    "LLM call failed with key index %d (%s), rotating to next key",
                    _current_key_index, type(exc).__name__,
                )
                _rotate_client()
                tried_keys += 1
                continue
            raise
