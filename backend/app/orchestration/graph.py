"""LangGraph DAG with QA feedback loop.

Flow: collect → analyze → write → filter → qa → (qa_router)
qa_router routes to END (pass) or back to collect/analyze/write (fail, up to MAX_RETRIES).
"""

from __future__ import annotations

import logging
from typing import Any

from langgraph.graph import END, StateGraph

from app.agents.analyst import AnalystAgent
from app.agents.collector import CollectorAgent
from app.agents.qa import QAAgent
from app.agents.writer import WriterAgent
from app.orchestration.state import PipelineState
from app.schemas.trace import EventType, TraceEvent

logger = logging.getLogger(__name__)

MAX_RETRIES = 2

# Singleton agent instances
_collector = CollectorAgent()
_analyst = AnalystAgent()
_writer = WriterAgent()
_qa = QAAgent()


async def collect_node(state: PipelineState) -> dict:
    """Run the Collector Agent."""
    logger.info("DAG: collect_node starting for task %s", state.get("task_id"))
    task = state.get("task", {})
    constraints = [c if isinstance(c, str) else str(c) for c in state.get("constraints", [])]

    result = await _collector.run({
        "target_product": task.get("target_product", ""),
        "competitors": task.get("competitors", []),
        "industry": task.get("industry", ""),
        "constraints": constraints,
    })

    existing_traces = state.get("traces", [])
    return {
        "sources": result["sources"],
        "traces": existing_traces + result["traces"],
        "status": "analyzing",
    }


async def analyze_node(state: PipelineState) -> dict:
    """Run the Analyst Agent."""
    logger.info("DAG: analyze_node starting for task %s", state.get("task_id"))
    constraints = [c if isinstance(c, str) else str(c) for c in state.get("constraints", [])]

    result = await _analyst.run({
        "sources": state.get("sources", []),
        "constraints": constraints,
    })

    existing_traces = state.get("traces", [])
    return {
        "analysis": result["analysis"],
        "traces": existing_traces + result["traces"],
        "status": "writing",
    }


async def write_node(state: PipelineState) -> dict:
    """Run the Writer Agent."""
    logger.info("DAG: write_node starting for task %s", state.get("task_id"))
    task = state.get("task", {})
    constraints = [c if isinstance(c, str) else str(c) for c in state.get("constraints", [])]

    result = await _writer.run({
        "analysis": state.get("analysis", {}),
        "target_product": task.get("target_product", ""),
        "task_id": state.get("task_id", ""),
        "constraints": constraints,
    })

    existing_traces = state.get("traces", [])
    return {
        "report": result["report"],
        "traces": existing_traces + result["traces"],
        "status": "filtering",
    }


async def filter_node(state: PipelineState) -> dict:
    """Remove claims without evidence from the report."""
    logger.info("DAG: filter_node starting for task %s", state.get("task_id"))
    report = state.get("report", {})
    removed_count = 0

    filtered_sections = []
    for section in report.get("sections", []):
        claims = section.get("claims", [])
        valid_claims = [c for c in claims if c.get("evidence_ids")]
        removed_count += len(claims) - len(valid_claims)
        filtered_sections.append({**section, "claims": valid_claims})

    report = {**report, "sections": filtered_sections}

    existing_traces = state.get("traces", [])
    trace = TraceEvent(
        agent_name="filter",
        event_type=EventType.OUTPUT,
        output_summary=f"Filtered {removed_count} claims without evidence",
    )

    return {
        "report": report,
        "traces": existing_traces + [trace.model_dump()],
        "status": "qa",
    }


async def qa_node(state: PipelineState) -> dict:
    """Run the QA Agent."""
    logger.info("DAG: qa_node starting for task %s", state.get("task_id"))

    result = await _qa.run({
        "report": state.get("report", {}),
        "sources": state.get("sources", []),
        "task_id": state.get("task_id", ""),
        "retry_count": state.get("retry_count", 0),
    })

    qa_feedback = result["qa_feedback"]
    new_metrics = result["metrics"]
    existing_traces = state.get("traces", [])

    update: dict[str, Any] = {
        "qa_feedback": qa_feedback,
        "metrics": new_metrics,
        "traces": existing_traces + result["traces"],
    }

    if not qa_feedback.get("passed"):
        # Save current metrics as previous for improvement tracking
        update["previous_metrics"] = state.get("metrics", {})
        update["handoff"] = result.get("handoff", {})
        update["constraints"] = state.get("constraints", []) + qa_feedback.get("constraints", [])
        update["retry_count"] = state.get("retry_count", 0) + 1
        # Mark failed if retries exhausted, otherwise retrying
        if update["retry_count"] > MAX_RETRIES:
            update["status"] = "failed"
        else:
            update["status"] = "retrying"
    else:
        # Record improvement delta if this was a retry
        if state.get("retry_count", 0) > 0:
            prev = state.get("previous_metrics", {})
            prev_cov = prev.get("evidence_coverage_rate", 0)
            new_cov = new_metrics.get("evidence_coverage_rate", 0)
            delta = round(new_cov - prev_cov, 4)
            improvement_trace = TraceEvent(
                agent_name="qa",
                event_type=EventType.OUTPUT,
                output_summary=f"Improvement after retry: evidence_coverage delta={delta:+.2%}",
            )
            update["traces"] = update["traces"] + [improvement_trace.model_dump()]
        update["status"] = "completed"

    return update


def qa_router(state: PipelineState) -> str:
    """Route after QA: END if passed or retries exhausted, else back to target agent."""
    qa = state.get("qa_feedback", {})
    retry_count = state.get("retry_count", 0)

    if qa.get("passed"):
        return END

    if retry_count > MAX_RETRIES:
        logger.warning("Task %s: max retries exceeded, ending as failed", state.get("task_id"))
        return END

    target = qa.get("retry_target", "writer")
    if target in ("collector", "collect"):
        return "collect"
    elif target in ("analyst", "analyze"):
        return "analyze"
    else:
        return "write"


def build_graph() -> StateGraph:
    """Build DAG with QA feedback loop."""
    graph = StateGraph(PipelineState)

    graph.add_node("collect", collect_node)
    graph.add_node("analyze", analyze_node)
    graph.add_node("write", write_node)
    graph.add_node("filter", filter_node)
    graph.add_node("qa", qa_node)

    graph.set_entry_point("collect")
    graph.add_edge("collect", "analyze")
    graph.add_edge("analyze", "write")
    graph.add_edge("write", "filter")
    graph.add_edge("filter", "qa")
    graph.add_conditional_edges("qa", qa_router)

    return graph


# Compiled graph — ready to invoke
pipeline_graph = build_graph().compile()
