"""API endpoints for preset demo scenarios."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.demo.scenarios import DEMO_SCENARIOS, get_scenario

router = APIRouter()


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class DemoSource(BaseModel):
    id: str
    type: str
    title: str
    url: str | None = None
    content_snippet: str = ""
    reliability_score: float = Field(ge=0.0, le=1.0, default=0.5)


class DemoClaim(BaseModel):
    id: str = ""
    content: str
    evidence_ids: list[str] = []
    confidence: float = Field(ge=0.0, le=1.0, default=0.9)
    category: str = ""


class DemoReportSection(BaseModel):
    title: str
    content: str = ""
    claims: list[DemoClaim] = []
    subsections: list["DemoReportSection"] = []


DemoReportSection.model_rebuild()


class DemoReport(BaseModel):
    title: str = ""
    executive_summary: str = ""
    sections: list[DemoReportSection] = []


class DemoTraceEvent(BaseModel):
    event_type: str
    agent_name: str = ""
    input_summary: str = ""
    output_summary: str = ""
    token_count: int | None = None
    duration: float | None = None


class DemoTrace(BaseModel):
    agent_name: str
    events: list[DemoTraceEvent] = []
    total_duration: float | None = None
    total_tokens: int | None = None
    status: str = "completed"


class DemoMetrics(BaseModel):
    source_count: int = 0
    claim_count: int = 0
    evidence_coverage_rate: float = 0.0
    manual_correction_count: int = 0


class DemoScenarioSummary(BaseModel):
    id: str
    name: str
    description: str
    industry: str
    target_product: str
    competitors: list[dict]
    focus_areas: list[str]


class DemoScenarioDetail(BaseModel):
    id: str
    name: str
    description: str
    industry: str
    target_product: str
    competitors: list[dict]
    our_product_notes: str = ""
    focus_areas: list[str]
    sources: list[DemoSource]
    report: DemoReport
    traces: list[DemoTrace]
    metrics: DemoMetrics


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=list[DemoScenarioSummary])
async def list_demos():
    """List all available demo scenarios."""
    return [
        DemoScenarioSummary(
            id=s["id"],
            name=s["name"],
            description=s["description"],
            industry=s["industry"],
            target_product=s["target_product"],
            competitors=s["competitors"],
            focus_areas=s["focus_areas"],
        )
        for s in DEMO_SCENARIOS
    ]


@router.get("/{scenario_id}", response_model=DemoScenarioDetail)
async def get_demo(scenario_id: str):
    """Get a full demo scenario with cached report."""
    scenario = get_scenario(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Demo scenario not found")
    return DemoScenarioDetail(**scenario)
