from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from app.agents.base import BaseAgent
from app.llm.client import (
    LLMContentFilterError,
    LLMResponse,
    _is_content_filter_error,
    call_llm,
)


class _DummySchema(BaseModel):
    ok: bool


class _DummyAgent(BaseAgent):
    name = "dummy"
    system_prompt = "system"

    async def run(self, input_data):
        return input_data


def test_detects_provider_block_message():
    assert _is_content_filter_error(RuntimeError("Your request was blocked."))


async def test_call_llm_raises_content_filter_error_after_retry(monkeypatch):
    class FakeCompletions:
        def __init__(self) -> None:
            self.calls: list[dict] = []

        async def create(self, **kwargs):
            self.calls.append(kwargs)
            raise RuntimeError("Your request was blocked.")

    completions = FakeCompletions()
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))

    monkeypatch.setattr("app.llm.client._clients", [client])
    monkeypatch.setattr("app.llm.client._current_key_index", 0)
    monkeypatch.setattr("app.llm.client.settings.LLM_MOCK", False)

    messages = [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "A" * 800},
    ]

    with pytest.raises(LLMContentFilterError):
        await call_llm(messages)

    assert len(completions.calls) == 2
    retry_prompt = completions.calls[1]["messages"][-1]["content"]
    assert retry_prompt.endswith("[Content truncated for safety]")


async def test_base_agent_reports_provider_block_cleanly(monkeypatch):
    async def fake_call_llm(messages, **kwargs):
        raise LLMContentFilterError("Your request was blocked.")

    monkeypatch.setattr("app.agents.base.call_llm", fake_call_llm)

    agent = _DummyAgent()
    with pytest.raises(RuntimeError, match="Request blocked by the model provider after 1 attempt"):
        await agent.call_and_validate("hello", _DummySchema)


async def test_base_agent_bumps_max_tokens_on_truncated_json(monkeypatch):
    """A truncated (unterminated) JSON response should raise max_tokens on retry,
    then succeed once the model returns complete JSON."""
    seen_max_tokens: list[int] = []

    async def fake_call_llm(messages, *, max_tokens=4096, **kwargs):
        seen_max_tokens.append(max_tokens)
        if len(seen_max_tokens) == 1:
            # First attempt: truncated JSON (unterminated string)
            content = '{"ok": true, "note": "this string never clo'
        else:
            content = '{"ok": true}'
        return LLMResponse(
            content=content,
            input_tokens=10,
            output_tokens=max_tokens,  # pretend we hit the cap
            model="test-model",
            duration=0.1,
        )

    monkeypatch.setattr("app.agents.base.call_llm", fake_call_llm)

    agent = _DummyAgent()
    validated, _resp, _traces = await agent.call_and_validate(
        "hello", _DummySchema, max_tokens=4096
    )

    assert validated.ok is True
    assert seen_max_tokens[0] == 4096
    assert seen_max_tokens[1] == 8192  # doubled after detecting truncation


