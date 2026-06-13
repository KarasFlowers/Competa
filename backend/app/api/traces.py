from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.database import TaskModel, TraceModel

router = APIRouter()


class TraceResponse(BaseModel):
    id: str
    task_id: str
    agent_name: str
    events: list
    total_duration: float | None
    total_tokens: int | None
    status: str

    model_config = {"from_attributes": True}


@router.get("/{task_id}/traces", response_model=list[TraceResponse])
async def get_traces(task_id: str, session: AsyncSession = Depends(get_session)):
    task = await session.get(TaskModel, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    result = await session.execute(
        select(TraceModel).where(TraceModel.task_id == task_id)
    )
    return result.scalars().all()
