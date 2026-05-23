"""Tests for DAG execution — end-to-end with QA ratchet mechanism."""

import pytest
from app.graph.builder import build_graph
from app.llm.adapter import MockLLM


class TestDAGExecution:
    async def test_full_dag_with_qa_retry(self):
        """End-to-end DAG: must go through QA reject → retry → QA pass."""
        llm = MockLLM()
        graph = build_graph(llm)

        initial_state = {
            "task_id": "dag-test-001",
            "industry": "Technology",
            "target_product": "ProductX",
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

        final_state = await graph.ainvoke(initial_state)

        # DAG completed
        assert final_state is not None

        # Sources collected
        assert len(final_state["sources"]) > 0

        # Analysis produced
        assert final_state["analysis"] is not None

        # Report generated
        assert final_state["report"] is not None

        # QA feedback present and passed (after retry)
        qa = final_state["qa_feedback"]
        assert qa is not None
        assert qa["passed"] is True

        # Ratchet: constraints accumulated from first QA failure
        assert len(final_state["constraints"]) > 0

        # Retry happened: retry_count should be 1
        assert final_state["retry_count"] == 1

        # Traces: should have traces for each agent execution
        # Expected: collect, analyze, write, qa(fail), collect(retry),
        #           analyze, write, qa(pass) = 8 traces
        assert len(final_state["traces"]) >= 6

    async def test_dag_agent_names_in_traces(self):
        """Verify all expected agents appear in traces."""
        llm = MockLLM()
        graph = build_graph(llm)

        initial_state = {
            "task_id": "trace-test-001",
            "industry": "Fintech",
            "target_product": "FinApp",
            "competitors": ["RivalA"],
            "sources": [],
            "analysis": None,
            "report": None,
            "qa_feedback": None,
            "constraints": [],
            "traces": [],
            "retry_count": 0,
            "max_retries": 2,
        }

        final_state = await graph.ainvoke(initial_state)

        agent_names = {t.agent_name for t in final_state["traces"]}
        assert "collector" in agent_names
        assert "analyst" in agent_names
        assert "writer" in agent_names
        assert "qa" in agent_names

    async def test_dag_constraint_has_required_fields(self):
        """Verify ratchet constraints have expected structure."""
        llm = MockLLM()
        graph = build_graph(llm)

        initial_state = {
            "task_id": "constraint-test",
            "industry": "E-commerce",
            "target_product": "ShopApp",
            "competitors": ["StoreX"],
            "sources": [],
            "analysis": None,
            "report": None,
            "qa_feedback": None,
            "constraints": [],
            "traces": [],
            "retry_count": 0,
            "max_retries": 2,
        }

        final_state = await graph.ainvoke(initial_state)

        assert len(final_state["constraints"]) > 0
        constraint = final_state["constraints"][0]
        assert "constraint_type" in constraint
        assert "constraint_value" in constraint
        assert "applied_to" in constraint
        assert "source_issue" in constraint
