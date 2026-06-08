import asyncio
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.db.session import get_session
from app.models.database import (
    AnalysisModel,
    ConstraintModel,
    InterviewModel,
    MetricsModel,
    ReportModel,
    SourceModel,
    SurveyModel,
    TaskModel,
    TraceModel,
)
from app.orchestration.runner import run_pipeline

logger = logging.getLogger(__name__)

router = APIRouter()
STARTABLE_TASK_STATUSES = ("pending", "failed", "completed")
ACTIVE_TASK_STATUSES = (
    "collecting",
    "surveying",
    "interviewing",
    "fieldwork",
    "analyzing",
    "writing",
    "screenshotting",
    "filtering",
    "qa",
    "retrying",
)

# Track background tasks to prevent GC from cancelling them
_background_tasks: set[asyncio.Task] = set()


def _create_tracked_task(coro) -> asyncio.Task:
    """Create an asyncio.Task that is tracked to prevent premature GC."""
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return task


def _find_claim_recursive(sections: list[dict], claim_id: str) -> dict | None:
    """Recursively search sections and subsections for a claim by ID."""
    for section in sections:
        for claim in section.get("claims", []):
            if claim.get("id") == claim_id:
                return claim
        found = _find_claim_recursive(section.get("subsections", []), claim_id)
        if found:
            return found
    return None


# ---------------------------------------------------------------------------
# Request / Response schemas (API-level, separate from domain schemas)
# ---------------------------------------------------------------------------

class CompetitorInput(BaseModel):
    """Structured competitor entry — mirrors competitorsmart's CompetitorInfo."""
    name: str
    category: str = "direct"  # direct | indirect | substitute
    website: str | None = None
    notes: str = ""  # free-form notes, sales intel, etc.
    tags: list[str] = Field(default_factory=list)


class TaskCreate(BaseModel):
    industry: str = ""
    target_product: str
    competitors: list[str | CompetitorInput] = Field(default_factory=list)
    our_product_notes: str = ""  # context about our own product


class TaskResponse(BaseModel):
    id: str
    industry: str
    target_product: str
    competitors: list[str | CompetitorInput]
    our_product_notes: str = ""
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskArtifactSummary(BaseModel):
    report: bool
    analysis: bool
    traces: bool
    survey: bool
    interview: bool


class TaskMetricsSummary(BaseModel):
    source_count: int
    claim_count: int
    evidence_coverage_rate: float
    manual_correction_count: int


class TaskOverviewItem(BaseModel):
    id: str
    industry: str
    target_product: str
    competitors: list[str | CompetitorInput]
    our_product_notes: str = ""
    status: str
    created_at: datetime
    updated_at: datetime
    metrics: TaskMetricsSummary | None = None
    artifacts: TaskArtifactSummary


class TaskOverviewStats(BaseModel):
    total_tasks: int
    active_tasks: int
    completed_tasks: int
    failed_tasks: int
    reports_ready: int
    avg_evidence_coverage: float | None = None
    status_counts: dict[str, int]


class TaskOverviewResponse(BaseModel):
    stats: TaskOverviewStats
    items: list[TaskOverviewItem]


def _build_task_id_set(values: list[str | None]) -> set[str]:
    return {value for value in values if value}


def _latest_by_task_id(records: list, task_id_attr: str, time_attr: str) -> dict[str, object]:
    latest: dict[str, object] = {}
    for record in sorted(
        records,
        key=lambda item: (
            getattr(item, task_id_attr),
            getattr(item, time_attr),
            getattr(item, "id", ""),
        ),
        reverse=True,
    ):
        task_id = getattr(record, task_id_attr)
        latest.setdefault(task_id, record)
    return latest


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(body: TaskCreate, session: AsyncSession = Depends(get_session)):
    # Normalize competitors: string → {"name": str}, CompetitorInput → dict
    competitors_data = []
    for c in body.competitors:
        if isinstance(c, str):
            competitors_data.append({"name": c, "category": "direct"})
        else:
            competitors_data.append(c.model_dump())
    task = TaskModel(
        industry=body.industry,
        target_product=body.target_product,
        competitors=competitors_data,
        our_product_notes=body.our_product_notes,
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


@router.get("/overview", response_model=TaskOverviewResponse)
async def get_tasks_overview(session: AsyncSession = Depends(get_session)):
    tasks_result = await session.execute(
        select(TaskModel).order_by(TaskModel.updated_at.desc(), TaskModel.created_at.desc())
    )
    tasks = tasks_result.scalars().all()

    metrics_result = await session.execute(select(MetricsModel))
    latest_metrics = _latest_by_task_id(
        metrics_result.scalars().all(),
        task_id_attr="task_id",
        time_attr="calculated_at",
    )

    report_ids = _build_task_id_set((await session.execute(select(ReportModel.task_id))).scalars().all())
    analysis_ids = _build_task_id_set((await session.execute(select(AnalysisModel.task_id))).scalars().all())
    trace_ids = _build_task_id_set((await session.execute(select(TraceModel.task_id))).scalars().all())
    survey_ids = _build_task_id_set((await session.execute(select(SurveyModel.task_id))).scalars().all())
    interview_ids = _build_task_id_set((await session.execute(select(InterviewModel.task_id))).scalars().all())

    items: list[TaskOverviewItem] = []
    status_counts: dict[str, int] = {}
    coverage_values: list[float] = []

    for task in tasks:
        status_counts[task.status] = status_counts.get(task.status, 0) + 1
        metrics_row = latest_metrics.get(task.id)
        metrics_summary = None
        if metrics_row:
            coverage = float(metrics_row.evidence_coverage_rate)
            coverage_values.append(coverage)
            metrics_summary = TaskMetricsSummary(
                source_count=metrics_row.source_count,
                claim_count=metrics_row.claim_count,
                evidence_coverage_rate=coverage,
                manual_correction_count=metrics_row.manual_correction_count,
            )

        items.append(
            TaskOverviewItem(
                id=task.id,
                industry=task.industry,
                target_product=task.target_product,
                competitors=task.competitors or [],
                our_product_notes=task.our_product_notes or "",
                status=task.status,
                created_at=task.created_at,
                updated_at=task.updated_at,
                metrics=metrics_summary,
                artifacts=TaskArtifactSummary(
                    report=task.id in report_ids,
                    analysis=task.id in analysis_ids,
                    traces=task.id in trace_ids,
                    survey=task.id in survey_ids,
                    interview=task.id in interview_ids,
                ),
            )
        )

    stats = TaskOverviewStats(
        total_tasks=len(tasks),
        active_tasks=sum(1 for task in tasks if task.status in ACTIVE_TASK_STATUSES),
        completed_tasks=sum(1 for task in tasks if task.status == "completed"),
        failed_tasks=sum(1 for task in tasks if task.status == "failed"),
        reports_ready=sum(1 for task in tasks if task.id in report_ids),
        avg_evidence_coverage=(
            round(sum(coverage_values) / len(coverage_values), 4)
            if coverage_values
            else None
        ),
        status_counts=status_counts,
    )

    return TaskOverviewResponse(stats=stats, items=items)


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


@router.post("/{task_id}/run", status_code=202)
async def run_task(task_id: str, session: AsyncSession = Depends(get_session)):
    """Trigger pipeline execution for a task (runs in background)."""
    task = await session.get(TaskModel, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    result = await session.execute(
        update(TaskModel)
        .where(
            TaskModel.id == task_id,
            TaskModel.status.in_(STARTABLE_TASK_STATUSES),
        )
        .values(status="collecting", updated_at=datetime.now(UTC))
    )

    if result.rowcount == 0:
        await session.rollback()
        current_task = await session.get(TaskModel, task_id)
        current_status = current_task.status if current_task else "unknown"
        raise HTTPException(
            status_code=409,
            detail=f"Task is already in '{current_status}' state, cannot restart",
        )

    for model in (
        SourceModel,
        ReportModel,
        TraceModel,
        MetricsModel,
        ConstraintModel,
    ):
        await session.execute(delete(model).where(model.task_id == task_id))

    await session.commit()

    # Launch pipeline in background with exception logging only after claim is committed.
    async def _safe_run():
        try:
            await run_pipeline(task_id)
        except Exception:
            logger.exception("Background pipeline failed for task %s", task_id)

    _create_tracked_task(_safe_run())
    return {"message": "Pipeline started", "task_id": task_id}


class TaskStatusResponse(BaseModel):
    id: str
    status: str
    target_product: str

    model_config = {"from_attributes": True}


@router.get("/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status(task_id: str, session: AsyncSession = Depends(get_session)):
    """Get current pipeline execution status."""
    task = await session.get(TaskModel, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


# ---------------------------------------------------------------------------
# Human correction endpoints
# ---------------------------------------------------------------------------

class CorrectionRequest(BaseModel):
    correction_type: str  # "add_source" | "edit_claim" | "add_constraint"
    data: dict


class CorrectionResponse(BaseModel):
    message: str
    task_id: str


@router.post("/{task_id}/corrections", response_model=CorrectionResponse)
async def submit_correction(
    task_id: str,
    body: CorrectionRequest,
    session: AsyncSession = Depends(get_session),
):
    """Submit a human correction (add source, edit claim, or add constraint)."""
    task = await session.get(TaskModel, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    ctype = body.correction_type
    data = body.data

    if ctype == "add_source":
        source = SourceModel(
            task_id=task_id,
            type=data.get("type", "url"),
            url=data.get("url"),
            title=data.get("title", ""),
            content_snippet=data.get("content_snippet", ""),
            reliability_score=data.get("reliability_score", 0.5),
        )
        session.add(source)
        # Add constraint to incorporate new source on next run
        constraint = ConstraintModel(
            task_id=task_id,
            constraint_type="human",
            constraint_value="CONSTRAINT: incorporate newly provided source into analysis",
            applied_to="collector",
        )
        session.add(constraint)

    elif ctype == "edit_claim":
        # Find report and update the specific claim
        result = await session.execute(
            select(ReportModel).where(ReportModel.task_id == task_id)
            .order_by(ReportModel.created_at.desc())
        )
        report = result.scalars().first()
        if report:
            content = report.content or {}
            claim_id = data.get("claim_id", "")
            new_content = data.get("content", "")
            claim = _find_claim_recursive(content.get("sections", []), claim_id)
            if claim:
                claim["content"] = new_content
            report.content = content
            flag_modified(report, "content")
        # Increment manual_correction_count on metrics
        mresult = await session.execute(
            select(MetricsModel).where(MetricsModel.task_id == task_id)
            .order_by(MetricsModel.calculated_at.desc())
        )
        metrics = mresult.scalars().first()
        if metrics:
            metrics.manual_correction_count += 1

    elif ctype == "add_constraint":
        constraint = ConstraintModel(
            task_id=task_id,
            constraint_type="human",
            constraint_value=data.get("constraint", ""),
            applied_to=data.get("applied_to", "writer"),
        )
        session.add(constraint)

    else:
        raise HTTPException(status_code=400, detail=f"Unknown correction_type: {ctype}")

    await session.commit()
    return CorrectionResponse(message="Correction applied", task_id=task_id)


# ---------------------------------------------------------------------------
# DAG structure endpoint
# ---------------------------------------------------------------------------

# Static DAG definition — mirrors graph.py build_graph()
_DAG_NODES = [
    {"id": "collector", "label": "信息采集", "type": "agent"},
    {"id": "survey", "label": "问卷设计", "type": "agent"},
    {"id": "interview", "label": "访谈设计", "type": "agent"},
    {"id": "fieldwork", "label": "调研执行", "type": "agent"},
    {"id": "analyst", "label": "分析", "type": "agent"},
    {"id": "writer", "label": "报告撰写", "type": "agent"},
    {"id": "screenshot", "label": "截图采集", "type": "tool"},
    {"id": "filter", "label": "证据过滤", "type": "tool"},
    {"id": "qa", "label": "质检", "type": "agent"},
]

_DAG_EDGES = [
    {"source": "collector", "target": "survey"},
    {"source": "survey", "target": "interview"},
    {"source": "interview", "target": "fieldwork"},
    {"source": "fieldwork", "target": "analyst"},
    {"source": "analyst", "target": "writer"},
    {"source": "writer", "target": "screenshot"},
    {"source": "screenshot", "target": "filter"},
    {"source": "filter", "target": "qa"},
    {"source": "qa", "target": "collector", "label": "retry"},
    {"source": "qa", "target": "analyst", "label": "retry"},
    {"source": "qa", "target": "writer", "label": "retry"},
]

# Map task.status to the currently-running DAG node
_STATUS_TO_RUNNING_NODE = {
    "collecting": "collector",
    "surveying": "survey",
    "interviewing": "interview",
    "fieldwork": "fieldwork",
    "analyzing": "analyst",
    "writing": "writer",
    "screenshotting": "screenshot",
    "filtering": "filter",
    "retrying": "qa",  # retrying means QA just failed
    "qa": "qa",
}


class DagNodeResponse(BaseModel):
    id: str
    label: str
    type: str  # "agent" | "tool"
    status: str  # "pending" | "running" | "completed" | "failed"


class DagEdgeResponse(BaseModel):
    source: str
    target: str
    label: str | None = None


class DagStructureResponse(BaseModel):
    nodes: list[DagNodeResponse]
    edges: list[DagEdgeResponse]


@router.get("/{task_id}/dag", response_model=DagStructureResponse)
async def get_task_dag(task_id: str, session: AsyncSession = Depends(get_session)):
    """Return the DAG structure with node statuses inferred from task state and traces."""
    task = await session.get(TaskModel, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Determine which agents have completed from trace events
    trace_result = await session.execute(
        select(TraceModel).where(TraceModel.task_id == task_id)
    )
    completed_agents: set[str] = set()
    failed_agents: set[str] = set()
    for trace in trace_result.scalars().all():
        for event in trace.events or []:
            if not isinstance(event, dict):
                continue
            agent = event.get("agent_name", "")
            etype = event.get("event_type", "")
            if etype == "output" and agent:
                completed_agents.add(agent)
            if etype == "error" and agent:
                failed_agents.add(agent)

    # Determine the currently-running node from task status
    running_node = _STATUS_TO_RUNNING_NODE.get(task.status, "")

    # Build node statuses
    nodes: list[DagNodeResponse] = []
    for n in _DAG_NODES:
        nid = n["id"]
        if nid in failed_agents:
            status = "failed"
        elif nid in completed_agents:
            status = "completed"
        elif nid == running_node:
            status = "running"
        else:
            status = "pending"
        nodes.append(DagNodeResponse(
            id=nid, label=n["label"], type=n["type"], status=status,
        ))

    edges = [DagEdgeResponse(**e) for e in _DAG_EDGES]
    return DagStructureResponse(nodes=nodes, edges=edges)


@router.post("/{task_id}/rerun", status_code=202)
async def rerun_task(task_id: str, session: AsyncSession = Depends(get_session)):
    """Re-run pipeline preserving existing sources and constraints."""
    task = await session.get(TaskModel, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status not in STARTABLE_TASK_STATUSES:
        raise HTTPException(
            status_code=409,
            detail=f"Task is in '{task.status}' state, cannot rerun",
        )

    # Only clear report/traces/metrics, keep sources and constraints
    for model in (ReportModel, TraceModel, MetricsModel):
        await session.execute(delete(model).where(model.task_id == task_id))

    task.status = "collecting"
    task.updated_at = datetime.now(UTC)
    await session.commit()

    async def _safe_run():
        try:
            await run_pipeline(task_id)
        except Exception:
            logger.exception("Background rerun failed for task %s", task_id)

    _create_tracked_task(_safe_run())
    return {"message": "Pipeline rerun started", "task_id": task_id}


# ---------------------------------------------------------------------------
# Survey & Interview endpoints
# ---------------------------------------------------------------------------

@router.get("/{task_id}/survey")
async def get_task_survey(task_id: str, session: AsyncSession = Depends(get_session)):
    """Return the survey questionnaire generated for this task."""
    task = await session.get(TaskModel, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    result = await session.execute(
        select(SurveyModel).where(SurveyModel.task_id == task_id)
    )
    survey = result.scalar_one_or_none()
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    return survey.content


@router.get("/{task_id}/interview")
async def get_task_interview(task_id: str, session: AsyncSession = Depends(get_session)):
    """Return the interview guide generated for this task."""
    task = await session.get(TaskModel, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    result = await session.execute(
        select(InterviewModel).where(InterviewModel.task_id == task_id)
    )
    interview = result.scalar_one_or_none()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview guide not found")
    return interview.content


@router.get("/{task_id}/analysis")
async def get_task_analysis(task_id: str, session: AsyncSession = Depends(get_session)):
    """Return the structured competitive analysis (feature trees / pricing /
    personas / SWOT) used to build the comparison matrix and SWOT quadrants."""
    task = await session.get(TaskModel, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    result = await session.execute(
        select(AnalysisModel)
        .where(AnalysisModel.task_id == task_id)
        .order_by(AnalysisModel.created_at.desc(), AnalysisModel.id.desc())
    )
    analysis = result.scalars().first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis.content
