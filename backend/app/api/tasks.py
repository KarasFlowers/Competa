import asyncio
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.database import TaskModel
from app.orchestration.runner import run_pipeline

logger = logging.getLogger(__name__)

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


@router.post("/{task_id}/run", status_code=202)
async def run_task(task_id: str, session: AsyncSession = Depends(get_session)):
    """Trigger pipeline execution for a task (runs in background)."""
    task = await session.get(TaskModel, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status not in ("pending", "failed"):
        raise HTTPException(
            status_code=409,
            detail=f"Task is already in '{task.status}' state, cannot restart",
        )
    # Launch pipeline in background with exception logging
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
