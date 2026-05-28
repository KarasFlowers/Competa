"""QA Agent — validates report completeness, evidence coverage, and computes metrics."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from app.agents.base import BaseAgent
from app.llm.prompts import QA_SYSTEM, build_qa_prompt
from app.orchestration.constraint_resolver import (
    build_handoff,
    determine_retry_target,
    issues_to_constraints,
)


class QAMetrics(BaseModel):
    source_count: int = 0
    claim_count: int = 0
    claims_with_evidence: int = 0
    evidence_coverage_rate: float = 0.0


class QAIssueOutput(BaseModel):
    issue_type: str
    field_path: str = ""
    description: str
    severity: str = "warning"


class QAOutput(BaseModel):
    passed: bool
    issues: list[QAIssueOutput] = Field(default_factory=list)
    metrics: QAMetrics = Field(default_factory=QAMetrics)
    summary: str = ""


class QAAgent(BaseAgent):
    name = "qa"
    system_prompt = QA_SYSTEM

    async def run(self, input_data: dict[str, Any]) -> dict:
        """Run QA check.

        input_data should contain:
            - report: dict
            - sources: list[dict]
            - task_id: str
            - retry_count: int (optional, for handoff generation)
        """
        report = input_data.get("report", {})
        sources = input_data.get("sources", [])
        task_id = input_data.get("task_id", "")
        retry_count = input_data.get("retry_count", 0)

        report_json = json.dumps(report, ensure_ascii=False, indent=2)
        sources_json = json.dumps(sources, ensure_ascii=False, indent=2)

        user_prompt = build_qa_prompt(report_json, sources_json)

        validated, llm_resp, traces = await self.call_and_validate(
            user_prompt=user_prompt,
            output_schema=QAOutput,
        )

        issues_dicts = [i.model_dump() for i in validated.issues]

        if validated.passed:
            retry_target = ""
            constraint_strs: list[str] = []
            handoff_dict: dict = {}
        else:
            retry_target = determine_retry_target(issues_dicts)
            constraint_strs = issues_to_constraints(issues_dicts)
            handoff = build_handoff(issues_dicts, retry_count)
            handoff_dict = handoff.model_dump()

        qa_feedback = {
            "passed": validated.passed,
            "issues": issues_dicts,
            "retry_target": retry_target,
            "constraints": constraint_strs,
        }

        metrics = {
            "task_id": task_id,
            "source_count": validated.metrics.source_count,
            "claim_count": validated.metrics.claim_count,
            "evidence_coverage_rate": validated.metrics.evidence_coverage_rate,
            "manual_correction_count": 0,
        }

        return {
            "qa_feedback": qa_feedback,
            "metrics": metrics,
            "handoff": handoff_dict if not validated.passed else {},
            "traces": [t.model_dump() for t in traces],
            "_llm_response": {
                "input_tokens": llm_resp.input_tokens,
                "output_tokens": llm_resp.output_tokens,
                "duration": llm_resp.duration,
            },
        }
