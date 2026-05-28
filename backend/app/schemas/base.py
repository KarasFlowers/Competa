from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Annotated, Union

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Source / Evidence / Claim
# ---------------------------------------------------------------------------

class SourceType(str, Enum):
    URL = "url"
    DOCUMENT = "document"
    INTERVIEW = "interview"
    SURVEY = "survey"


class Source(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    type: SourceType
    url: str | None = None
    title: str
    content_snippet: str = ""
    fetched_at: datetime = Field(default_factory=datetime.utcnow)


class Evidence(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    source_id: str
    quote: str
    relevance_score: float = Field(ge=0.0, le=1.0, default=0.5)


class Claim(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    content: str
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    category: str = ""


# ---------------------------------------------------------------------------
# AgentMessage payload subtypes
# ---------------------------------------------------------------------------

class CollectRequest(BaseModel):
    task_id: str
    target_products: list[str]
    source_types: list[SourceType] = Field(default_factory=lambda: list(SourceType))
    focus_areas: list[str] = Field(default_factory=list)


class CollectResult(BaseModel):
    sources: list[Source]
    coverage_note: str = ""


class AnalyzeRequest(BaseModel):
    task_id: str
    sources: list[Source]
    analysis_dimensions: list[str] = Field(
        default_factory=lambda: ["features", "pricing", "personas", "swot"]
    )


class AnalyzeResult(BaseModel):
    feature_trees: list = Field(default_factory=list)
    pricing_models: list = Field(default_factory=list)
    personas: list = Field(default_factory=list)
    swot_analyses: list = Field(default_factory=list)


class WriteRequest(BaseModel):
    task_id: str
    analysis: AnalyzeResult
    report_style: str = "professional"


class WriteResult(BaseModel):
    report: dict  # serialised Report — avoids circular import


class QAFeedback(BaseModel):
    passed: bool
    issues: list = Field(default_factory=list)  # list[QAIssue]
    retry_target: str = ""
    constraints: list = Field(default_factory=list)  # list[ConstraintRule]


# ---------------------------------------------------------------------------
# AgentMessage — discriminated union on message_type
# ---------------------------------------------------------------------------

class MessageType(str, Enum):
    COLLECT_REQUEST = "collect_request"
    COLLECT_RESULT = "collect_result"
    ANALYZE_REQUEST = "analyze_request"
    ANALYZE_RESULT = "analyze_result"
    WRITE_REQUEST = "write_request"
    WRITE_RESULT = "write_result"
    QA_FEEDBACK = "qa_feedback"


MessagePayload = Annotated[
    Union[
        CollectRequest,
        CollectResult,
        AnalyzeRequest,
        AnalyzeResult,
        WriteRequest,
        WriteResult,
        QAFeedback,
    ],
    Field(discriminator=None),
]


class AgentMessage(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    from_agent: str
    to_agent: str
    message_type: MessageType
    payload: MessagePayload
    timestamp: datetime = Field(default_factory=datetime.utcnow)
