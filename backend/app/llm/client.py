from __future__ import annotations

import time
from dataclasses import dataclass

from openai import AsyncOpenAI

from app.config import settings

# Mock mode flag
_is_mock = False


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


_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL or None,
        )
    return _client


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
    """Call LLM via OpenAI-compatible API.

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

    client = _get_client()
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
