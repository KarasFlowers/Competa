"""Task runner — loads task from DB, runs the DAG, persists results."""

from __future__ import annotations

import logging
import time

from fastapi.encoders import jsonable_encoder

from app.db.session import async_session
from app.guardrails.redact import safe_error_message
from app.models.database import (
    AnalysisModel,
    ConstraintModel,
    InterviewModel,
    MetricsModel,
    ReportModel,
    RunHistoryModel,
    SourceModel,
    SurveyModel,
    TaskModel,
    TraceModel,
)
from app.orchestration.graph import pipeline_graph
from app.orchestration.state import PipelineState
from app.schemas.trace import EventType, TraceEvent
from sqlalchemy import delete, select

logger = logging.getLogger(__name__)


async def _next_run_index(session, task_id: str) -> int:
    result = await session.execute(
        select(RunHistoryModel.run_index)
        .where(RunHistoryModel.task_id == task_id)
        .order_by(RunHistoryModel.run_index.desc())
    )
    latest = result.scalars().first()
    return (latest or 0) + 1


def _merge_state_update(final_state: PipelineState, chunk: dict) -> None:
    if not chunk:
        return

    payloads = []
    if all(isinstance(value, dict) for value in chunk.values()):
        payloads.extend(chunk.values())
    else:
        payloads.append(chunk)

    for payload in payloads:
        final_state.update(payload)


def _build_trace_events(final_state: PipelineState, error_message: str | None = None) -> list[dict]:
    trace_events = list(final_state.get("traces", []))
    if error_message:
        trace_events.append(
            TraceEvent(
                agent_name="pipeline",
                event_type=EventType.ERROR,
                error_message=error_message,
            ).model_dump()
        )
    return trace_events


def _serialize_trace_events(trace_events: list[dict]) -> list[dict]:
    return jsonable_encoder(trace_events)


async def run_pipeline(task_id: str) -> None:
    """Execute the full pipeline for a task.

    Loads task from DB, runs LangGraph DAG, and persists
    sources / report / traces / metrics / constraints.
    """
    async with async_session() as session:
        started_at = time.monotonic()
        # Load task
        task = await session.get(TaskModel, task_id)
        if not task:
            logger.error("Task %s not found", task_id)
            return

        try:
            # Load existing sources and constraints (for rerun scenarios)
            existing_srcs = await session.execute(
                select(SourceModel).where(SourceModel.task_id == task_id)
            )
            existing_src_rows = existing_srcs.scalars().all()
            existing_sources = [
                {"id": s.id, "type": s.type, "url": s.url, "title": s.title,
                 "content_snippet": s.content_snippet, "reliability_score": s.reliability_score,
                 "included_in_analysis": s.included_in_analysis,
                 "curation_reason": s.curation_reason,
                 "curation_tags": s.curation_tags or [],
                 "curated_excerpt": s.curated_excerpt or "",
                 "fetched_at": str(s.fetched_at)}
                for s in existing_src_rows
            ]
            existing_src_by_id = {s.id: s for s in existing_src_rows}
            existing_cons = await session.execute(
                select(ConstraintModel).where(ConstraintModel.task_id == task_id)
            )
            existing_constraints = [
                c.constraint_value for c in existing_cons.scalars().all()
            ]

            # Build initial state
            initial_state: PipelineState = {
                "task_id": task_id,
                "task": {
                    "target_product": task.target_product,
                    "target_website": task.target_website or "",
                    "competitors": task.competitors or [],
                    "industry": task.industry or "",
                    "focus_areas": task.focus_areas or [],
                    "our_product_notes": task.our_product_notes or "",
                },
                "sources": existing_sources,
                "curated_sources": [],
                "curation_summary": {},
                "survey": {},
                "interview": {},
                "analysis": {},
                "report": {},
                "qa_feedback": {},
                "metrics": {},
                "previous_metrics": {},
                "handoff": {},
                "traces": [],
                "status": "collecting",
                "error": "",
                "retry_count": 0,
                "constraints": existing_constraints,
                "screenshot_paths": [],
            }
            final_state: PipelineState = dict(initial_state)

            # Run the graph and persist intermediate statuses as each node finishes.
            async for chunk in pipeline_graph.astream(initial_state, stream_mode="updates"):
                _merge_state_update(final_state, chunk)
                next_status = final_state.get("status")
                if next_status and task.status != next_status:
                    task.status = next_status
                    await session.commit()

            # Persist sources (preserve Pydantic ID so evidence_ids in claims resolve)
            # Skip sources that already exist in DB (rerun scenario)
            for src_data in final_state.get("sources", []):
                source = existing_src_by_id.get(src_data.get("id"))
                if source is None:
                    source = SourceModel(
                        id=src_data.get("id"),  # preserve original ID for citation linking
                        task_id=task_id,
                    )
                    session.add(source)
                source.type = src_data.get("type", "url")
                source.url = src_data.get("url")
                source.title = src_data.get("title", "")
                source.content_snippet = src_data.get("content_snippet", "")
                source.reliability_score = src_data.get("reliability_score", 0.5)
                source.included_in_analysis = bool(src_data.get("included_in_analysis", False))
                source.curation_reason = src_data.get("curation_reason", "")
                source.curation_tags = src_data.get("curation_tags", []) or []
                source.curated_excerpt = src_data.get("curated_excerpt", "")

            # Persist survey
            survey_data = final_state.get("survey", {})
            if survey_data:
                await session.execute(delete(SurveyModel).where(SurveyModel.task_id == task_id))
                survey = SurveyModel(
                    task_id=task_id,
                    content=jsonable_encoder(survey_data),
                )
                session.add(survey)

            # Persist interview
            interview_data = final_state.get("interview", {})
            if interview_data:
                await session.execute(delete(InterviewModel).where(InterviewModel.task_id == task_id))
                interview = InterviewModel(
                    task_id=task_id,
                    content=jsonable_encoder(interview_data),
                )
                session.add(interview)

            # Persist structured analysis (feature trees / pricing / personas / SWOT)
            analysis_data = final_state.get("analysis", {})
            if analysis_data:
                await session.execute(delete(AnalysisModel).where(AnalysisModel.task_id == task_id))
                analysis = AnalysisModel(
                    task_id=task_id,
                    content=jsonable_encoder(analysis_data),
                )
                session.add(analysis)

            # Persist report
            report_data = final_state.get("report", {})
            if report_data:
                await session.execute(delete(ReportModel).where(ReportModel.task_id == task_id))
                report = ReportModel(
                    task_id=task_id,
                    title=report_data.get("title", "Competitive Analysis Report"),
                    content=jsonable_encoder(report_data),
                    status="final" if final_state.get("qa_feedback", {}).get("passed") else "draft",
                )
                session.add(report)

            # Persist traces
            trace_events = final_state.get("traces", [])
            if trace_events:
                serialized_trace_events = _serialize_trace_events(trace_events)
                trace = TraceModel(
                    task_id=task_id,
                    agent_name="pipeline",
                    events=serialized_trace_events,
                    total_duration=round(time.monotonic() - started_at, 3),
                    total_tokens=sum(
                        event.get("token_count", 0)
                        for event in trace_events
                        if isinstance(event, dict) and event.get("token_count")
                    ),
                    status="completed" if final_state.get("status") == "completed" else "failed",
                )
                session.add(trace)

            # Persist metrics
            metrics_data = final_state.get("metrics", {})
            if metrics_data:
                await session.execute(delete(MetricsModel).where(MetricsModel.task_id == task_id))
                metrics = MetricsModel(
                    task_id=task_id,
                    source_count=metrics_data.get("source_count", 0),
                    claim_count=metrics_data.get("claim_count", 0),
                    evidence_coverage_rate=metrics_data.get("evidence_coverage_rate", 0.0),
                    manual_correction_count=task.manual_correction_count or 0,
                )
                session.add(metrics)

            # Persist ratchet constraints (deduplicate against existing)
            existing_constraint_values = set(existing_constraints)
            for constraint_str in final_state.get("constraints", []):
                if str(constraint_str) in existing_constraint_values:
                    continue
                constraint = ConstraintModel(
                    task_id=task_id,
                    constraint_type="ratchet",
                    constraint_value=str(constraint_str),
                    applied_to=final_state.get("qa_feedback", {}).get("retry_target", ""),
                )
                session.add(constraint)

            run_history = RunHistoryModel(
                task_id=task_id,
                run_index=await _next_run_index(session, task_id),
                status=final_state.get("status", "completed"),
                retry_count=final_state.get("retry_count", 0),
                source_count=metrics_data.get("source_count", len(final_state.get("curated_sources") or final_state.get("sources", []))) if metrics_data else len(final_state.get("curated_sources") or final_state.get("sources", [])),
                claim_count=metrics_data.get("claim_count", 0) if metrics_data else 0,
                evidence_coverage_rate=metrics_data.get("evidence_coverage_rate", 0.0) if metrics_data else 0.0,
                manual_correction_count=task.manual_correction_count or 0,
                qa_feedback=jsonable_encoder(final_state.get("qa_feedback", {}) or {}),
                handoff=jsonable_encoder(final_state.get("handoff", {}) or {}),
                curation_summary=jsonable_encoder(final_state.get("curation_summary", {}) or {}),
                constraints=[str(value) for value in final_state.get("constraints", [])],
                analysis=jsonable_encoder(analysis_data or {}),
                report=jsonable_encoder(report_data or {}),
                trace_events=jsonable_encoder(trace_events or []),
            )
            session.add(run_history)

            # Update task status
            task.status = final_state.get("status", "completed")
            task.last_qa_feedback = final_state.get("qa_feedback", {}) or {}
            task.last_handoff = final_state.get("handoff", {}) or {}
            task.last_curation_summary = final_state.get("curation_summary", {}) or {}
            await session.commit()

            logger.info(
                "Pipeline completed for task %s — status: %s, retries: %d",
                task_id,
                task.status,
                final_state.get("retry_count", 0),
            )

        except Exception as e:
            logger.exception("Pipeline failed for task %s: %s", task_id, safe_error_message(e))
            await session.rollback()
            task.status = "failed"
            failed_events = _build_trace_events(
                final_state if "final_state" in locals() else {},
                error_message=safe_error_message(e),
            )
            if failed_events:
                serialized_failed_events = _serialize_trace_events(failed_events)
                session.add(
                    TraceModel(
                        task_id=task_id,
                        agent_name="pipeline",
                        events=serialized_failed_events,
                        total_duration=round(time.monotonic() - started_at, 3),
                        total_tokens=sum(
                            event.get("token_count", 0)
                            for event in failed_events
                            if isinstance(event, dict) and event.get("token_count")
                        ),
                        status="failed",
                    )
                )
            await session.commit()
