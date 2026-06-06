import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _gen_id() -> str:
    return uuid.uuid4().hex


class Base(DeclarativeBase):
    pass


class TaskModel(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_gen_id)
    industry: Mapped[str] = mapped_column(String(255), default="")
    target_product: Mapped[str] = mapped_column(String(255), default="")
    competitors: Mapped[dict] = mapped_column(JSON, default=list)
    our_product_notes: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class SourceModel(Base):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_gen_id)
    task_id: Mapped[str] = mapped_column(String(32), index=True)
    type: Mapped[str] = mapped_column(String(32), default="url")
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str] = mapped_column(String(512), default="")
    content_snippet: Mapped[str] = mapped_column(Text, default="")
    reliability_score: Mapped[float] = mapped_column(Float, default=0.5)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ReportModel(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_gen_id)
    task_id: Mapped[str] = mapped_column(String(32), index=True)
    title: Mapped[str] = mapped_column(String(512), default="")
    content: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class TraceModel(Base):
    __tablename__ = "traces"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_gen_id)
    task_id: Mapped[str] = mapped_column(String(32), index=True)
    agent_name: Mapped[str] = mapped_column(String(64), default="")
    events: Mapped[dict] = mapped_column(JSON, default=list)
    total_duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="running")


class ConstraintModel(Base):
    __tablename__ = "constraints"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_gen_id)
    task_id: Mapped[str] = mapped_column(String(32), index=True)
    rule_id: Mapped[str] = mapped_column(String(32), default="")
    source_issue: Mapped[dict] = mapped_column(JSON, default=dict)
    constraint_type: Mapped[str] = mapped_column(String(64), default="")
    constraint_value: Mapped[str] = mapped_column(Text, default="")
    applied_to: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class MetricsModel(Base):
    __tablename__ = "metrics"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_gen_id)
    task_id: Mapped[str] = mapped_column(String(32), index=True)
    source_count: Mapped[int] = mapped_column(Integer, default=0)
    claim_count: Mapped[int] = mapped_column(Integer, default=0)
    evidence_coverage_rate: Mapped[float] = mapped_column(Float, default=0.0)
    manual_correction_count: Mapped[int] = mapped_column(Integer, default=0)
    calculated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class SurveyModel(Base):
    __tablename__ = "surveys"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_gen_id)
    task_id: Mapped[str] = mapped_column(String(32), index=True)
    content: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class InterviewModel(Base):
    __tablename__ = "interviews"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_gen_id)
    task_id: Mapped[str] = mapped_column(String(32), index=True)
    content: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AnalysisModel(Base):
    """Structured competitive intelligence from the Analyst Agent.

    Stores the full AnalyzeResult (feature_trees / pricing_models / personas /
    swot_analyses) so the frontend can render the comparison matrix and SWOT
    quadrants — distinct from the narrative report produced by the Writer.
    """

    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_gen_id)
    task_id: Mapped[str] = mapped_column(String(32), index=True)
    content: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
