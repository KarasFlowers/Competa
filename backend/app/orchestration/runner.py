"""Task runner — loads task from DB, runs the DAG, persists results."""

from __future__ import annotations

import logging

from app.db.session import async_session
from app.models.database import (
    ConstraintModel,
    MetricsModel,
    ReportModel,
    SourceModel,
    TaskModel,
    TraceModel,
)
from app.orchestration.graph import pipeline_graph
from app.orchestration.state import PipelineState

logger = logging.getLogger(__name__)


async def run_pipeline(task_id: str) -> None:
    """Execute the full pipeline for a task.

    Loads task from DB, runs LangGraph DAG, and persists
    sources / report / traces / metrics / constraints.
    """
    async with async_session() as session:
        # Load task
        task = await session.get(TaskModel, task_id)
        if not task:
            logger.error("Task %s not found", task_id)
            return

        # Update status to running
        task.status = "collecting"
        await session.commit()

        try:
            # Build initial state
            initial_state: PipelineState = {
                "task_id": task_id,
                "task": {
                    "target_product": task.target_product,
                    "competitors": task.competitors or [],
                    "industry": task.industry or "",
                },
                "sources": [],
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
                "constraints": [],
            }

            # Run the graph
            final_state = await pipeline_graph.ainvoke(initial_state)

            # Persist sources (preserve Pydantic ID so evidence_ids in claims resolve)
            for src_data in final_state.get("sources", []):
                source = SourceModel(
                    id=src_data.get("id"),  # preserve original ID for citation linking
                    task_id=task_id,
                    type=src_data.get("type", "url"),
                    url=src_data.get("url"),
                    title=src_data.get("title", ""),
                    content_snippet=src_data.get("content_snippet", ""),
                )
                session.add(source)

            # Persist report
            report_data = final_state.get("report", {})
            if report_data:
                report = ReportModel(
                    task_id=task_id,
                    title=report_data.get("title", "Competitive Analysis Report"),
                    content=report_data,
                    status="final" if final_state.get("qa_feedback", {}).get("passed") else "draft",
                )
                session.add(report)

            # Persist traces
            trace_events = final_state.get("traces", [])
            if trace_events:
                trace = TraceModel(
                    task_id=task_id,
                    agent_name="pipeline",
                    events=trace_events,
                    status="completed",
                )
                session.add(trace)

            # Persist metrics
            metrics_data = final_state.get("metrics", {})
            if metrics_data:
                metrics = MetricsModel(
                    task_id=task_id,
                    source_count=metrics_data.get("source_count", 0),
                    claim_count=metrics_data.get("claim_count", 0),
                    evidence_coverage_rate=metrics_data.get("evidence_coverage_rate", 0.0),
                    manual_correction_count=0,
                )
                session.add(metrics)

            # Persist ratchet constraints
            for constraint_str in final_state.get("constraints", []):
                constraint = ConstraintModel(
                    task_id=task_id,
                    constraint_type="ratchet",
                    constraint_value=str(constraint_str),
                    applied_to=final_state.get("qa_feedback", {}).get("retry_target", ""),
                )
                session.add(constraint)

            # Update task status
            task.status = final_state.get("status", "completed")
            await session.commit()

            logger.info(
                "Pipeline completed for task %s — status: %s, retries: %d",
                task_id,
                task.status,
                final_state.get("retry_count", 0),
            )

        except Exception as e:
            logger.exception("Pipeline failed for task %s: %s", task_id, e)
            task.status = "failed"
            await session.commit()
