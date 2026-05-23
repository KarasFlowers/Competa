from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Annotated, Literal, Union

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
# MessageType enum (needed before payload subtypes)
# ---------------------------------------------------------------------------

class MessageType(str, Enum):
    COLLECT_REQUEST = "collect_request"
    COLLECT_RESULT = "collect_result"
    ANALYZE_REQUEST = "analyze_request"
    ANALYZE_RESULT = "analyze_result"
    WRITE_REQUEST = "write_request"
    WRITE_RESULT = "write_result"
    QA_FEEDBACK = "qa_feedback"


# ---------------------------------------------------------------------------
# AgentMessage payload subtypes
# ---------------------------------------------------------------------------

class CollectRequest(BaseModel):
    message_type: Literal[MessageType.COLLECT_REQUEST] = MessageType.COLLECT_REQUEST
    task_id: str
    target_products: list[str]
    source_types: list[SourceType] = Field(default_factory=lambda: list(SourceType))
    focus_areas: list[str] = Field(default_factory=list)


class CollectResult(BaseModel):
    message_type: Literal[MessageType.COLLECT_RESULT] = MessageType.COLLECT_RESULT
    sources: list[Source]
    coverage_note: str = ""


class AnalyzeRequest(BaseModel):
    message_type: Literal[MessageType.ANALYZE_REQUEST] = MessageType.ANALYZE_REQUEST
    task_id: str
    sources: list[Source]
    analysis_dimensions: list[str] = Field(
        default_factory=lambda: ["features", "pricing", "personas", "swot"]
    )


class AnalyzeResult(BaseModel):
    message_type: Literal[MessageType.ANALYZE_RESULT] = MessageType.ANALYZE_RESULT
    feature_trees: list["FeatureTree"] = Field(default_factory=list)
    pricing_models: list["PricingModel"] = Field(default_factory=list)
    personas: list["Persona"] = Field(default_factory=list)
    swot_analyses: list["SWOT"] = Field(default_factory=list)


class WriteRequest(BaseModel):
    message_type: Literal[MessageType.WRITE_REQUEST] = MessageType.WRITE_REQUEST
    task_id: str
    analysis: AnalyzeResult
    report_style: str = "professional"


class WriteResult(BaseModel):
    message_type: Literal[MessageType.WRITE_RESULT] = MessageType.WRITE_RESULT
    report: dict  # serialised Report — avoids circular import


class QAFeedback(BaseModel):
    message_type: Literal[MessageType.QA_FEEDBACK] = MessageType.QA_FEEDBACK
    passed: bool
    issues: list["QAIssue"] = Field(default_factory=list)
    retry_target: str = ""
    constraints: list["ConstraintRule"] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# AgentMessage — discriminated union on message_type
# ---------------------------------------------------------------------------

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
    Field(discriminator="message_type"),
]


class AgentMessage(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    from_agent: str
    to_agent: str
    message_type: MessageType
    payload: MessagePayload
    timestamp: datetime = Field(default_factory=datetime.utcnow)
