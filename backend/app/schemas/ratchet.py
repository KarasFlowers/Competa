from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class IssueType(str, Enum):
    MISSING_FIELD = "missing_field"
    MISSING_EVIDENCE = "missing_evidence"
    SCHEMA_VIOLATION = "schema_violation"
    LOW_COVERAGE = "low_coverage"


class Severity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"


class QAIssue(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    issue_type: IssueType
    field_path: str = ""
    description: str
    severity: Severity = Severity.WARNING


class ConstraintRule(BaseModel):
    rule_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    source_issue: QAIssue
    constraint_type: str
    constraint_value: str
    applied_to: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TaskMetrics(BaseModel):
    task_id: str
    source_count: int = 0
    claim_count: int = 0
    evidence_coverage_rate: float = Field(ge=0.0, le=1.0, default=0.0)
    manual_correction_count: int = 0
    calculated_at: datetime = Field(default_factory=datetime.utcnow)
