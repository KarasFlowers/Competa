from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.database import (
    TaskModel,
    SourceModel,
    ReportModel,
    TraceModel,
    ConstraintModel,
    MetricsModel,
)
from app.graph.builder import build_graph
from app.llm import get_llm

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response schemas (API-level, separate from domain schemas)
# ---------------------------------------------------------------------------

class TaskCreate(BaseModel):
    industry: str = ""
    target_product: str
    competitors: list[str] = Field(default_factory=list)


class TaskResponse(BaseModel):
    id: str
    industry: str
    target_product: str
    competitors: list
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(body: TaskCreate, session: AsyncSession = Depends(get_session)):
    task = TaskModel(
        industry=body.industry,
        target_product=body.target_product,
        competitors=body.competitors,
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


@router.get("", response_model=list[TaskResponse])
async def list_tasks(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(TaskModel).order_by(TaskModel.created_at.desc()))
    return result.scalars().all()


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str, session: AsyncSession = Depends(get_session)):
    task = await session.get(TaskModel, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/{task_id}/run", response_model=TaskResponse)
async def run_task(task_id: str, session: AsyncSession = Depends(get_session)):
    """Execute the competitive analysis DAG for a task."""
    task = await session.get(TaskModel, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status not in ("pending", "failed"):
        raise HTTPException(
            status_code=409,
            detail=f"Task is {task.status}, can only run pending/failed tasks",
        )

    # Mark as running
    task.status = "running"
    await session.commit()

    try:
        # Build and execute DAG
        llm = get_llm()
        graph = build_graph(llm)

        initial_state = {
            "task_id": task.id,
            "industry": task.industry,
            "target_product": task.target_product,
            "competitors": task.competitors if isinstance(task.competitors, list) else [],
            "sources": [],
            "analysis": None,
            "report": None,
            "qa_feedback": None,
            "constraints": [],
            "traces": [],
            "retry_count": 0,
            "max_retries": 1,
        }

        final_state = await graph.ainvoke(initial_state)

        # Persist results to DB
        await _persist_results(session, task.id, final_state)

        # Update task status
        task.status = "completed"
        await session.commit()
        await session.refresh(task)
        return task

    except Exception as exc:
        task.status = "failed"
        await session.commit()
        await session.refresh(task)
        raise HTTPException(status_code=500, detail=str(exc)[:500])


def _json_safe(obj: Any) -> Any:
    """Recursively convert datetime objects to ISO strings for JSON columns."""
    import datetime as _dt
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, _dt.datetime):
        return obj.isoformat()
    return obj


async def _persist_results(
    session: AsyncSession,
    task_id: str,
    state: dict,
) -> None:
    """Write DAG execution results to database."""

    # --- Sources ---
    sources = state.get("sources", [])
    for src in sources:
        src_data = src if isinstance(src, dict) else src.model_dump() if hasattr(src, "model_dump") else {}
        session.add(SourceModel(
            task_id=task_id,
            type=src_data.get("type", "url"),
            url=src_data.get("url"),
            title=src_data.get("title", ""),
            content_snippet=src_data.get("content_snippet", ""),
        ))

    # --- Report ---
    report_data = state.get("report")
    if report_data:
        report_dict = report_data if isinstance(report_data, dict) else {}
        inner = report_dict.get("report", report_dict)
        # Ensure content is JSON-safe (convert datetime strings etc.)
        inner = _json_safe(inner)
        session.add(ReportModel(
            task_id=task_id,
            title=inner.get("title", "Competitive Analysis Report") if isinstance(inner, dict) else "Report",
            content=inner,
            status="final",
        ))

    # --- Traces ---
    traces = state.get("traces", [])
    for trace in traces:
        trace_data = trace.model_dump(mode="json") if hasattr(trace, "model_dump") else trace
        status_val = trace_data.get("status", "completed")
        if hasattr(status_val, "value"):
            status_val = status_val.value
        session.add(TraceModel(
            task_id=task_id,
            agent_name=trace_data.get("agent_name", ""),
            events=trace_data.get("events", []),
            total_duration=trace_data.get("total_duration"),
            total_tokens=trace_data.get("total_tokens"),
            status=status_val,
        ))

    # --- Constraints ---
    constraints = state.get("constraints", [])
    for con in constraints:
        if hasattr(con, "model_dump"):
            con_data = con.model_dump(mode="json")
        elif isinstance(con, dict):
            con_data = con
        else:
            con_data = {}
        # Ensure source_issue is JSON-safe
        src_issue = con_data.get("source_issue", {})
        if hasattr(src_issue, "model_dump"):
            src_issue = src_issue.model_dump(mode="json")
        session.add(ConstraintModel(
            task_id=task_id,
            rule_id=con_data.get("rule_id", ""),
            source_issue=con_data.get("source_issue", {}),
            constraint_type=con_data.get("constraint_type", ""),
            constraint_value=con_data.get("constraint_value", ""),
            applied_to=con_data.get("applied_to", ""),
        ))

    # --- Metrics ---
    sources_list = state.get("sources", [])
    report_inner = state.get("report", {}) or {}
    if isinstance(report_inner, dict):
        report_content = report_inner.get("report", report_inner)
    else:
        report_content = {}
    sections = report_content.get("sections", []) if isinstance(report_content, dict) else []
    claim_count = sum(
        len(sec.get("claims", [])) for sec in sections if isinstance(sec, dict)
    )
    evidence_ids = []
    for sec in sections:
        if isinstance(sec, dict):
            for claim in sec.get("claims", []):
                if isinstance(claim, dict):
                    evidence_ids.extend(claim.get("evidence_ids", []))
    coverage = len(evidence_ids) / max(claim_count, 1)

    session.add(MetricsModel(
        task_id=task_id,
        source_count=len(sources_list),
        claim_count=claim_count,
        evidence_coverage_rate=min(coverage, 1.0),
    ))

    await session.commit()
