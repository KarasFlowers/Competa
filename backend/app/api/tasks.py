import asyncio
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.db.session import get_session
from app.models.database import (
    ConstraintModel,
    MetricsModel,
    ReportModel,
    SourceModel,
    TaskModel,
    TraceModel,
)
from app.orchestration.runner import run_pipeline

logger = logging.getLogger(__name__)

router = APIRouter()
STARTABLE_TASK_STATUSES = ("pending", "failed", "completed")


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
        .values(status="collecting", updated_at=datetime.utcnow())
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

    asyncio.create_task(_safe_run())
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
            for section in content.get("sections", []):
                for claim in section.get("claims", []):
                    if claim.get("id") == claim_id:
                        claim["content"] = new_content
                        break
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
    task.updated_at = datetime.utcnow()
    await session.commit()

    async def _safe_run():
        try:
            await run_pipeline(task_id)
        except Exception:
            logger.exception("Background rerun failed for task %s", task_id)

    asyncio.create_task(_safe_run())
    return {"message": "Pipeline rerun started", "task_id": task_id}
