from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.base import Claim


class ReportSection(BaseModel):
    title: str
    content: str = ""
    claims: list[Claim] = Field(default_factory=list)
    subsections: list[ReportSection] = Field(default_factory=list)


class Report(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    task_id: str
    title: str
    executive_summary: str = ""
    sections: list[ReportSection] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
