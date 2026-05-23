"""Tests for Agent implementations — input/output/trace generation."""

import pytest
from app.llm.adapter import MockLLM
from app.agents.collector import CollectorAgent
from app.agents.analyst import AnalystAgent
from app.agents.writer import WriterAgent
from app.agents.qa import QAAgent


@pytest.fixture
def mock_llm():
    return MockLLM()


def _base_state():
    return {
        "task_id": "test-task-001",
        "industry": "SaaS",
        "target_product": "MyProduct",
        "competitors": ["CompA", "CompB"],
        "sources": [],
        "analysis": None,
        "report": None,
        "qa_feedback": None,
        "constraints": [],
        "traces": [],
        "retry_count": 0,
        "max_retries": 2,
    }


class TestCollectorAgent:
    async def test_run_returns_sources(self, mock_llm):
        agent = CollectorAgent(mock_llm)
        state = _base_state()
        updates = await agent.run(state)
        assert "sources" in updates
        assert len(updates["sources"]) > 0
        assert "traces" in updates
        assert len(updates["traces"]) == 1
        assert updates["traces"][0].agent_name == "collector"
        assert updates["traces"][0].status.value == "completed"


class TestAnalystAgent:
    async def test_run_returns_analysis(self, mock_llm):
        agent = AnalystAgent(mock_llm)
        state = _base_state()
        updates = await agent.run(state)
        assert "analysis" in updates
        assert isinstance(updates["analysis"], dict)
        assert "traces" in updates
        assert updates["traces"][0].agent_name == "analyst"


class TestWriterAgent:
    async def test_run_returns_report(self, mock_llm):
        agent = WriterAgent(mock_llm)
        state = _base_state()
        updates = await agent.run(state)
        assert "report" in updates
        assert isinstance(updates["report"], dict)
        assert "traces" in updates
        assert updates["traces"][0].agent_name == "writer"


class TestQAAgent:
    async def test_first_call_fails_and_adds_constraints(self, mock_llm):
        agent = QAAgent(mock_llm)
        state = _base_state()
        updates = await agent.run(state)
        assert "qa_feedback" in updates
        qa = updates["qa_feedback"]
        assert qa["passed"] is False
        assert "constraints" in updates
        assert len(updates["constraints"]) > 0
        assert updates["retry_count"] == 1

    async def test_second_call_passes(self, mock_llm):
        agent = QAAgent(mock_llm)
        state = _base_state()
        # First call (fails)
        updates1 = await agent.run(state)
        # Merge updates into state
        state.update(updates1)
        # Second call (passes)
        updates2 = await agent.run(state)
        qa = updates2["qa_feedback"]
        assert qa["passed"] is True


class TestAgentTraceGeneration:
    async def test_trace_has_start_and_end_events(self, mock_llm):
        agent = CollectorAgent(mock_llm)
        state = _base_state()
        updates = await agent.run(state)
        trace = updates["traces"][0]
        event_types = [e.event_type.value for e in trace.events]
        assert "start" in event_types
        assert "end" in event_types
        assert trace.total_duration is not None
        assert trace.total_duration >= 0
