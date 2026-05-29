from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.database import MetricsModel, ReportModel, SourceModel

router = APIRouter()


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class ReportResponse(BaseModel):
    id: str
    task_id: str
    title: str
    content: dict
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SourceResponse(BaseModel):
    id: str
    task_id: str
    type: str
    url: str | None
    title: str
    content_snippet: str
    fetched_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/{task_id}/report", response_model=ReportResponse)
async def get_report(task_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(ReportModel)
        .where(ReportModel.task_id == task_id)
        .order_by(ReportModel.created_at.desc(), ReportModel.id.desc())
    )
    report = result.scalars().first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.get("/{task_id}/sources", response_model=list[SourceResponse])
async def get_sources(task_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(SourceModel).where(SourceModel.task_id == task_id)
    )
    return result.scalars().all()


@router.get("/{task_id}/sources/{source_id}", response_model=SourceResponse)
async def get_source(task_id: str, source_id: str, session: AsyncSession = Depends(get_session)):
    source = await session.get(SourceModel, source_id)
    if not source or source.task_id != task_id:
        raise HTTPException(status_code=404, detail="Source not found")
    return source


class MetricsResponse(BaseModel):
    id: str
    task_id: str
    source_count: int
    claim_count: int
    evidence_coverage_rate: float
    manual_correction_count: int
    calculated_at: datetime

    model_config = {"from_attributes": True}


@router.get("/{task_id}/metrics", response_model=MetricsResponse)
async def get_metrics(task_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(MetricsModel)
        .where(MetricsModel.task_id == task_id)
        .order_by(MetricsModel.calculated_at.desc(), MetricsModel.id.desc())
    )
    metrics = result.scalars().first()
    if not metrics:
        raise HTTPException(status_code=404, detail="Metrics not found")
    return metrics
