"""Analyst Agent — extracts structured competitive intelligence from collected sources."""

from __future__ import annotations

import json
from typing import Any

from app.agents.base import BaseAgent
from app.llm.prompts import ANALYST_SYSTEM, build_analyst_prompt
from app.schemas.base import AnalyzeResult


class AnalystAgent(BaseAgent):
    name = "analyst"
    system_prompt = ANALYST_SYSTEM

    async def run(self, input_data: dict[str, Any]) -> dict:
        """Run analysis.

        input_data should contain:
            - sources: list[dict]
            - constraints: list[str] (optional, ratchet constraints from QA)
        """
        sources = input_data.get("sources", [])
        # Pass structured summary, not full content
        sources_summary = json.dumps(sources, ensure_ascii=False, indent=2, default=str)

        user_prompt = build_analyst_prompt(sources_summary)

        # Inject ratchet constraints from previous QA feedback
        constraints = input_data.get("constraints", [])
        if constraints:
            user_prompt += "\n\nYou MUST satisfy these constraints:\n" + "\n".join(constraints)

        validated, llm_resp, traces = await self.call_and_validate(
            user_prompt=user_prompt,
            output_schema=AnalyzeResult,
        )

        return {
            "analysis": validated.model_dump(),
            "traces": [t.model_dump() for t in traces],
            "_llm_response": {
                "input_tokens": llm_resp.input_tokens,
                "output_tokens": llm_resp.output_tokens,
                "duration": llm_resp.duration,
            },
        }
