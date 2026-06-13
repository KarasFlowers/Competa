from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from app.agents.base import BaseAgent
from app.llm.client import (
    LLMContentFilterError,
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

