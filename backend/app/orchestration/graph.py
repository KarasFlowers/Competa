"""LangGraph DAG with QA feedback loop.

Flow: collect → survey → interview → fieldwork → curate → analyze → write → screenshot → filter → qa → (qa_router)
The fieldwork node simulates running the designed survey + interview and folds
the results back into the evidence pool as SURVEY/INTERVIEW sources.
qa_router routes to END (pass) or back to collect/analyze/write (fail, up to MAX_RETRIES).
"""

from __future__ import annotations

import logging
from typing import Any

from langgraph.graph import END, StateGraph

from app.agents.analyst import AnalystAgent
from app.agents.collector import CollectorAgent
from app.agents.fieldwork import FieldworkAgent
from app.agents.interview import InterviewAgent
from app.agents.qa import QAAgent
from app.agents.survey import SurveyAgent
from app.agents.writer import WriterAgent
from app.api.sse import publish_event as _publish_event
from app.guardrails.report_validator import validate_report_completeness
from app.guardrails.schema_enforcer import enforce_competitive_schema
from app.orchestration.state import PipelineState
from app.schemas.trace import EventType, TraceEvent
from app.services.curation import curate_sources, merge_source_sets
from app.services.screenshot import screenshot_webpages

logger = logging.getLogger(__name__)


def publish_event(task_id: str, event: dict) -> None:
    """Publish SSE event, silently ignoring failures."""
    try:
        _publish_event(task_id, event)
    except Exception:
        pass

MAX_RETRIES = 2
MAX_CONSTRAINTS = 10

# Singleton agent instances
_collector = CollectorAgent()
_survey = SurveyAgent()
_interview = InterviewAgent()
_fieldwork = FieldworkAgent()
_analyst = AnalystAgent()
_writer = WriterAgent()
_qa = QAAgent()


async def collect_node(state: PipelineState) -> dict:
    """Run the Collector Agent."""
    task_id = state.get("task_id", "")
    logger.info("DAG: collect_node starting for task %s", task_id)
    publish_event(task_id, {"agent": "collector", "status": "running"})
    task = state.get("task", {})
    constraints = [c if isinstance(c, str) else str(c) for c in state.get("constraints", [])]

    result = await _collector.run({
        "target_product": task.get("target_product", ""),
        "target_website": task.get("target_website", ""),
        "competitors": task.get("competitors", []),
        "industry": task.get("industry", ""),
        "our_product_notes": task.get("our_product_notes", ""),
        "focus_areas": task.get("focus_areas"),
        "constraints": constraints,
    })

    llm_info = result.get("_llm_response", {})
    publish_event(task_id, {
        "agent": "collector", "status": "completed",
        "duration": llm_info.get("duration"),
        "tokens": (llm_info.get("input_tokens", 0) or 0) + (llm_info.get("output_tokens", 0) or 0),
    })
    existing_traces = state.get("traces", [])
    merged_sources = merge_source_sets(state.get("sources", []), result["sources"])
    return {
        "sources": merged_sources,
        "traces": existing_traces + result["traces"],
        "status": "surveying",
    }


async def survey_node(state: PipelineState) -> dict:
    """Run the Survey Agent — design a competitive analysis questionnaire."""
    task_id = state.get("task_id", "")
    logger.info("DAG: survey_node starting for task %s", task_id)
    publish_event(task_id, {"agent": "survey", "status": "running"})
    task = state.get("task", {})

    result = await _survey.run({
        "target_product": task.get("target_product", ""),
        "competitors": task.get("competitors", []),
        "industry": task.get("industry", ""),
        "focus_areas": task.get("focus_areas"),
        "our_product_notes": task.get("our_product_notes", ""),
    })

    llm_info = result.get("_llm_response", {})
    publish_event(task_id, {
        "agent": "survey", "status": "completed",
        "duration": llm_info.get("duration"),
        "tokens": (llm_info.get("input_tokens", 0) or 0) + (llm_info.get("output_tokens", 0) or 0),
    })
    existing_traces = state.get("traces", [])
    return {
        "survey": result["survey"],
        "traces": existing_traces + result["traces"],
        "status": "interviewing",
    }


async def interview_node(state: PipelineState) -> dict:
    """Run the Interview Agent — design a semi-structured interview guide."""
    task_id = state.get("task_id", "")
    logger.info("DAG: interview_node starting for task %s", task_id)
    publish_event(task_id, {"agent": "interview", "status": "running"})
    task = state.get("task", {})

    # Pass survey data if available (for targeted interview questions informed by survey)
    survey_data = state.get("survey", {})
    survey_questions = survey_data.get("questions", []) if survey_data else []

    result = await _interview.run({
        "target_product": task.get("target_product", ""),
        "competitors": task.get("competitors", []),
        "industry": task.get("industry", ""),
        "survey_questions": survey_questions if survey_questions else None,
        "our_product_notes": task.get("our_product_notes", ""),
    })

    llm_info = result.get("_llm_response", {})
    publish_event(task_id, {
        "agent": "interview", "status": "completed",
        "duration": llm_info.get("duration"),
        "tokens": (llm_info.get("input_tokens", 0) or 0) + (llm_info.get("output_tokens", 0) or 0),
    })
    existing_traces = state.get("traces", [])
    return {
        "interview": result["interview"],
        "traces": existing_traces + result["traces"],
        "status": "fieldwork",
    }


async def fieldwork_node(state: PipelineState) -> dict:
    """Run the Fieldwork Agent — simulate the designed survey + interview.

    Produces synthetic-but-realistic research results and folds them back into
    the evidence pool as SURVEY/INTERVIEW sources, so the Analyst's structured
    output is grounded in primary-research signals (not just web collection).
    """
    task_id = state.get("task_id", "")
    logger.info("DAG: fieldwork_node starting for task %s", task_id)
    publish_event(task_id, {"agent": "fieldwork", "status": "running"})
    task = state.get("task", {})

    result = await _fieldwork.run({
        "target_product": task.get("target_product", ""),
        "competitors": task.get("competitors", []),
        "survey": state.get("survey", {}),
        "interview": state.get("interview", {}),
        "personas": state.get("analysis", {}).get("personas", []),
        "our_product_notes": task.get("our_product_notes", ""),
    })

    new_sources = result.get("sources", [])
    merged_sources = merge_source_sets(state.get("sources", []), new_sources)

    llm_info = result.get("_llm_response", {})
    publish_event(task_id, {
        "agent": "fieldwork", "status": "completed",
        "duration": llm_info.get("duration"),
        "tokens": (llm_info.get("input_tokens", 0) or 0) + (llm_info.get("output_tokens", 0) or 0),
        "added_sources": len(new_sources),
    })
    existing_traces = state.get("traces", [])
    return {
        "fieldwork": result["fieldwork"],
        "sources": merged_sources,
        "traces": existing_traces + result["traces"],
        "status": "curating",
    }


async def curate_node(state: PipelineState) -> dict:
    """Deterministically curate evidence before passing it to Analyst."""
    task_id = state.get("task_id", "")
    logger.info("DAG: curate_node starting for task %s", task_id)
    publish_event(task_id, {"agent": "curator", "status": "running"})

    raw_sources = state.get("sources", [])
    curated = curate_sources(raw_sources)
    curated_sources = curated.sources
    summary = curated.summary

    existing_traces = state.get("traces", [])
    trace = TraceEvent(
        agent_name="curator",
        event_type=EventType.OUTPUT,
        output_summary=(
            f"Curated {summary.get('kept_count', 0)}/{summary.get('input_count', 0)} sources; "
            f"removed {summary.get('removed_count', 0)}"
        ),
        output_data=summary,
    )
    publish_event(task_id, {
        "agent": "curator",
        "status": "completed",
        "kept_sources": summary.get("kept_count", 0),
        "removed_sources": summary.get("removed_count", 0),
    })
    return {
        "sources": curated.all_sources,
        "curated_sources": curated_sources,
        "curation_summary": summary,
        "traces": existing_traces + [trace.model_dump()],
        "status": "analyzing",
    }


async def analyze_node(state: PipelineState) -> dict:
    """Run the Analyst Agent."""
    task_id = state.get("task_id", "")
    logger.info("DAG: analyze_node starting for task %s", task_id)
    publish_event(task_id, {"agent": "analyst", "status": "running"})
    constraints = [c if isinstance(c, str) else str(c) for c in state.get("constraints", [])]
    sources_for_analysis = state.get("curated_sources") or state.get("sources", [])

    result = await _analyst.run({
        "sources": sources_for_analysis,
        "constraints": constraints,
    })

    llm_info = result.get("_llm_response", {})
    publish_event(task_id, {
        "agent": "analyst", "status": "completed",
        "duration": llm_info.get("duration"),
        "tokens": (llm_info.get("input_tokens", 0) or 0) + (llm_info.get("output_tokens", 0) or 0),
    })
    existing_traces = state.get("traces", [])
    return {
        "analysis": result["analysis"],
        "traces": existing_traces + result["traces"],
        "status": "writing",
    }


async def write_node(state: PipelineState) -> dict:
    """Run the Writer Agent."""
    task_id = state.get("task_id", "")
    logger.info("DAG: write_node starting for task %s", task_id)
    publish_event(task_id, {"agent": "writer", "status": "running"})
    task = state.get("task", {})
    constraints = [c if isinstance(c, str) else str(c) for c in state.get("constraints", [])]

    result = await _writer.run({
        "analysis": state.get("analysis", {}),
        "target_product": task.get("target_product", ""),
        "task_id": task_id,
        "constraints": constraints,
        "sources": state.get("curated_sources") or state.get("sources", []),
    })

    llm_info = result.get("_llm_response", {})
    publish_event(task_id, {
        "agent": "writer", "status": "completed",
        "duration": llm_info.get("duration"),
        "tokens": (llm_info.get("input_tokens", 0) or 0) + (llm_info.get("output_tokens", 0) or 0),
    })
    existing_traces = state.get("traces", [])
    return {
        "report": result["report"],
        "traces": existing_traces + result["traces"],
        "status": "screenshotting",
    }


def _filter_sections_recursive(sections: list[dict]) -> tuple[list[dict], int]:
    """Recursively filter claims without evidence from sections and subsections.

    Returns (filtered_sections, removed_count).
    Accepts dicts or Pydantic models — normalises to dict on entry.
    """
    removed = 0
    filtered: list[dict] = []
    for section in sections:
        # Normalise: Pydantic model → dict
        s = section.model_dump() if hasattr(section, 'model_dump') else section
        if not isinstance(s, dict):
            s = dict(s) if hasattr(s, '__iter__') else {}
        claims = s.get("claims", [])
        valid_claims = [c for c in claims if c.get("evidence_ids")]
        removed += len(claims) - len(valid_claims)

        sub_sections = s.get("subsections", [])
        filtered_subs, sub_removed = _filter_sections_recursive(sub_sections)
        removed += sub_removed

        filtered.append({**s, "claims": valid_claims, "subsections": filtered_subs})
    return filtered, removed


async def screenshot_node(state: PipelineState) -> dict:
    """Capture screenshots of competitor websites for visual evidence.

    Degrades gracefully: skips silently when Playwright isn't installed
    (common on dev machines / headless servers).
    """
    task_id = state.get("task_id", "")
    logger.info("DAG: screenshot_node starting for task %s", task_id)
    publish_event(task_id, {"agent": "screenshot", "status": "running"})

    screenshot_results: list[dict[str, str | None]] = []
    try:
        urls_to_screenshot: list[str] = []
        competitors = state.get("task", {}).get("competitors", [])
        for c in competitors:
            if isinstance(c, dict) and c.get("website"):
                urls_to_screenshot.append(c["website"])

        sources = state.get("curated_sources") or state.get("sources", [])
        for s in sources[:5]:
            url = s.get("url", "")
            if url and url not in urls_to_screenshot:
                urls_to_screenshot.append(url)

        urls_to_screenshot = urls_to_screenshot[:8]

        if urls_to_screenshot:
            screenshot_results = await screenshot_webpages(urls_to_screenshot, task_id)
    except Exception:
        logger.info("Screenshot batch skipped (non-critical): %s", task_id)

    successful = [r for r in screenshot_results if r.get("path")]
    existing_traces = state.get("traces", [])
    trace = TraceEvent(
        agent_name="screenshot",
        event_type=EventType.OUTPUT,
        output_summary=f"Captured {len(successful)} screenshots",
    )

    publish_event(task_id, {
        "agent": "screenshot", "status": "completed",
        "screenshots_captured": len(successful),
    })
    return {
        "screenshot_paths": screenshot_results,
        "traces": existing_traces + [trace.model_dump()],
        "status": "filtering",
    }


async def filter_node(state: PipelineState) -> dict:
    """Remove claims without evidence from the report."""
    task_id = state.get("task_id", "")
    logger.info("DAG: filter_node starting for task %s", task_id)
    publish_event(task_id, {"agent": "filter", "status": "running"})
    report = state.get("report", {})

    filtered_sections, removed_count = _filter_sections_recursive(
        report.get("sections", [])
    )
    report = {**report, "sections": filtered_sections}

    existing_traces = state.get("traces", [])
    trace = TraceEvent(
        agent_name="filter",
        event_type=EventType.OUTPUT,
        output_summary=f"Filtered {removed_count} claims without evidence",
    )

    publish_event(task_id, {
        "agent": "filter", "status": "completed",
        "removed_claims": removed_count,
    })
    return {
        "report": report,
        "traces": existing_traces + [trace.model_dump()],
        "status": "qa",
    }


async def qa_node(state: PipelineState) -> dict:
    """Run the QA Agent with deterministic hard validation + LLM soft check."""
    task_id = state.get("task_id", "")
    logger.info("DAG: qa_node starting for task %s", task_id)
    publish_event(task_id, {"agent": "qa", "status": "running"})

    report = state.get("report", {})
    sources = state.get("curated_sources") or state.get("sources", [])

    # --- Deterministic hard validation (code-based, no LLM) ---
    hard_issues = validate_report_completeness(report, sources)
    if hard_issues:
        logger.info(
            "DAG: qa_node report validation found %d issue(s) for task %s",
            len(hard_issues), task_id,
        )

    # --- Competitive knowledge schema enforcement ---
    analysis = state.get("analysis", {})
    competitors = state.get("task", {}).get("competitors", [])
    schema_issues = enforce_competitive_schema(analysis, competitors)
    if schema_issues:
        logger.info(
            "DAG: qa_node schema enforcement found %d issue(s) for task %s",
            len(schema_issues), task_id,
        )
        hard_issues.extend(schema_issues)

    # --- LLM-based soft QA check ---
    result = await _qa.run({
        "report": report,
        "sources": sources,
        "task_id": task_id,
        "retry_count": state.get("retry_count", 0),
    })

    qa_feedback = result["qa_feedback"]
    new_metrics = result["metrics"]
    existing_traces = state.get("traces", [])

    # Merge hard-validated issues into LLM QA feedback
    if hard_issues:
        # Add hard issues that the LLM didn't already catch
        llm_issue_keys = {
            (i.get("issue_type"), i.get("field_path"))
            for i in qa_feedback.get("issues", [])
        }
        for hi in hard_issues:
            key = (hi["issue_type"], hi["field_path"])
            if key not in llm_issue_keys:
                qa_feedback["issues"].append(hi)
        # If any hard issue is critical, force passed=False
        if any(i.get("severity") == "critical" for i in hard_issues):
            qa_feedback["passed"] = False
        # Convert hard issues to constraint strings for retry guidance
        from app.orchestration.constraint_resolver import issues_to_constraints
        hard_constraints = issues_to_constraints(hard_issues)
        if hard_constraints:
            existing = qa_feedback.get("constraints", [])
            qa_feedback["constraints"] = list(dict.fromkeys(existing + hard_constraints))

    update: dict[str, Any] = {
        "qa_feedback": qa_feedback,
        "metrics": new_metrics,
        "traces": existing_traces + result["traces"],
    }

    if not qa_feedback.get("passed"):
        # Save current metrics as previous for improvement tracking
        update["previous_metrics"] = state.get("metrics", {})
        update["handoff"] = result.get("handoff", {})
        # Deduplicate and cap constraints to prevent prompt bloat
        existing_constraints = state.get("constraints", [])
        new_constraints = qa_feedback.get("constraints", [])
        merged = list(dict.fromkeys(existing_constraints + new_constraints))
        update["constraints"] = merged[-MAX_CONSTRAINTS:] if len(merged) > MAX_CONSTRAINTS else merged
        update["retry_count"] = state.get("retry_count", 0) + 1
        # Mark failed if retries exhausted, otherwise retrying
        if update["retry_count"] >= MAX_RETRIES:
            update["status"] = "failed"
        else:
            update["status"] = "retrying"
        publish_event(task_id, {
            "agent": "qa", "status": "completed",
            "passed": False, "retry_target": qa_feedback.get("retry_target", ""),
            "retry_count": update["retry_count"],
        })
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
        publish_event(task_id, {
            "agent": "qa", "status": "completed", "passed": True,
            "evidence_coverage_rate": new_metrics.get("evidence_coverage_rate", 0),
        })

    return update


def qa_router(state: PipelineState) -> str:
    """Route after QA: END if passed or retries exhausted, else back to target agent."""
    qa = state.get("qa_feedback", {})
    retry_count = state.get("retry_count", 0)

    if qa.get("passed"):
        return END

    if retry_count >= MAX_RETRIES:
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
    graph.add_node("survey", survey_node)
    graph.add_node("interview", interview_node)
    graph.add_node("fieldwork", fieldwork_node)
    graph.add_node("curate", curate_node)
    graph.add_node("analyze", analyze_node)
    graph.add_node("write", write_node)
    graph.add_node("screenshot", screenshot_node)
    graph.add_node("filter", filter_node)
    graph.add_node("qa", qa_node)

    graph.set_entry_point("collect")
    graph.add_edge("collect", "survey")
    graph.add_edge("survey", "interview")
    graph.add_edge("interview", "fieldwork")
    graph.add_edge("fieldwork", "curate")
    graph.add_edge("curate", "analyze")
    graph.add_edge("analyze", "write")
    graph.add_edge("write", "screenshot")
    graph.add_edge("screenshot", "filter")
    graph.add_edge("filter", "qa")
    graph.add_conditional_edges("qa", qa_router)

    return graph


# Compiled graph — ready to invoke
pipeline_graph = build_graph().compile()
