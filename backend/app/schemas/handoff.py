"""Handoff — structured rework instruction from QA to target Agent."""

from __future__ import annotations

from pydantic import BaseModel, Field


class HandoffInstruction(BaseModel):
    """Structured rework directive passed from QA to the next Agent on retry."""

    target_agent: str
    issue_type: str
    failed_fields: list[str] = Field(default_factory=list)
    evidence_requirements: str = ""
    max_retries: int = 2
    constraints: list[str] = Field(default_factory=list)
