"""DAG Builder — constructs LangGraph StateGraph for competitive analysis.

Inspired by:
- LangGraph StateGraph + conditional edges
- Conductor deterministic routing (zero-token orchestration)
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from app.agents.collector import CollectorAgent
from app.agents.analyst import AnalystAgent
from app.agents.writer import WriterAgent
from app.agents.qa import QAAgent
from app.graph.state import GraphState
from app.llm.adapter import BaseLLM


def _qa_router(state: GraphState) -> str:
    """Deterministic QA routing — zero token cost (ref: Conductor).

    Routes based on qa_feedback.passed and retry_count:
    - passed=true  → END
    - passed=false AND retry_count < max_retries → retry_target
    - passed=false AND retry_count >= max_retries → END (graceful degradation)
    """
    qa_feedback = state.get("qa_feedback")
    if qa_feedback is None:
        return END

    passed = qa_feedback.get("passed", True) if isinstance(qa_feedback, dict) else True
    if passed:
        return END

    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 1)
    if retry_count >= max_retries:
        return END

    retry_target = ""
    if isinstance(qa_feedback, dict):
        retry_target = qa_feedback.get("retry_target", "")

    if retry_target in ("collect", "analyze", "write"):
        return retry_target

    # Default: retry from write (most issues are in writing quality)
    return "write"


def build_graph(llm: BaseLLM) -> Any:
    """Build and compile the competitive analysis DAG.

    Flow: START → collect → analyze → write → qa → (END or retry)
    """
    collector = CollectorAgent(llm)
    analyst = AnalystAgent(llm)
    writer = WriterAgent(llm)
    qa = QAAgent(llm)

    graph = StateGraph(GraphState)

    # Add nodes
    graph.add_node("collect", collector.run)
    graph.add_node("analyze", analyst.run)
    graph.add_node("write", writer.run)
    graph.add_node("qa", qa.run)

    # Linear edges: START → collect → analyze → write → qa
    graph.set_entry_point("collect")
    graph.add_edge("collect", "analyze")
    graph.add_edge("analyze", "write")
    graph.add_edge("write", "qa")

    # Conditional edge from qa: deterministic routing
    graph.add_conditional_edges(
        "qa",
        _qa_router,
        {
            END: END,
            "collect": "collect",
            "analyze": "analyze",
            "write": "write",
        },
    )

    return graph.compile()
