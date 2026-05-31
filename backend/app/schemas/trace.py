from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field


class EventType(str, Enum):
    START = "start"
    END = "end"
    ERROR = "error"
    OUTPUT = "output"


class TraceStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TraceEvent(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    agent_name: str
    event_type: EventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    input_summary: str | None = None
    output_summary: str | None = None
    token_count: int | None = None
    error_message: str | None = None
    prompt: str | None = None
    input_data: dict | None = None
    output_data: dict | None = None
    duration: float | None = None
    retry_attempt: int | None = None


class AgentTrace(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    agent_name: str
    task_id: str
    events: list[TraceEvent] = Field(default_factory=list)
    total_duration: float | None = None
    total_tokens: int | None = None
    status: TraceStatus = TraceStatus.RUNNING
