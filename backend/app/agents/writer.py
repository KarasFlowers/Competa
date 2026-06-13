"""Writer Agent — generates structured competitive analysis report with citations."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from app.agents.base import BaseAgent
from app.llm.prompts import WRITER_SYSTEM, build_writer_prompt


class ClaimOutput(BaseModel):
    """Structured claim with mandatory content and optional evidence linkage."""

    id: str = ""
    content: str
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: float = 0.5
    category: str = ""


class ReportSectionOutput(BaseModel):
    """Structured report section with nested claims and subsections."""

    title: str
    content: str = ""
    claims: list[ClaimOutput] = Field(default_factory=list)
    subsections: list["ReportSectionOutput"] = Field(default_factory=list)


# Allow recursive model
ReportSectionOutput.model_rebuild()


class WriterReportOutput(BaseModel):
    """Schema for Writer LLM output (without task_id/generated_at which are added later)."""

    title: str
    executive_summary: str = ""
    sections: list[ReportSectionOutput] = Field(default_factory=list)


class WriterAgent(BaseAgent):
    name = "writer"
    system_prompt = WRITER_SYSTEM

    async def run(self, input_data: dict[str, Any]) -> dict:
        """Run report writing.

        input_data should contain:
            - analysis: dict (AnalyzeResult)
            - target_product: str
            - task_id: str
            - sources: list[dict] (optional, for evidence citation)
        """
        analysis = input_data.get("analysis", {})
        target_product = input_data.get("target_product", "")
        task_id = input_data.get("task_id", "")
        sources = input_data.get("sources", [])

        # Build source reference list (id + title only, for citation)
        source_refs = [
            {"id": s.get("id"), "title": s.get("title", ""), "type": s.get("type", "url")}
            for s in (sources or []) if s.get("id")
        ]
        sources_json = json.dumps(source_refs, ensure_ascii=False, indent=2, default=str) if source_refs else None

        analysis_json = json.dumps(analysis, ensure_ascii=False, indent=2, default=str)
        user_prompt = build_writer_prompt(analysis_json, target_product, sources_json)

        # Inject ratchet constraints from previous QA feedback
        constraints = input_data.get("constraints", [])
        if constraints:
            user_prompt += "\n\nYou MUST satisfy these constraints:\n" + "\n".join(constraints)

        validated, llm_resp, traces = await self.call_and_validate(
            user_prompt=user_prompt,
            output_schema=WriterReportOutput,
            max_tokens=16384,
        )

        report = {
            "task_id": task_id,
            "title": validated.title,
            "executive_summary": validated.executive_summary,
            "sections": validated.sections,
        }

        return {
            "report": report,
            "traces": [t.model_dump() for t in traces],
            "_llm_response": {
                "input_tokens": llm_resp.input_tokens,
                "output_tokens": llm_resp.output_tokens,
                "duration": llm_resp.duration,
            },
        }
