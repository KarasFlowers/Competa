"""Collector Agent — gathers competitive intelligence from multiple source types."""

from __future__ import annotations

import json
from typing import Any

from app.agents.base import BaseAgent
from app.llm.prompts import COLLECTOR_SYSTEM, build_collector_prompt
from app.schemas.base import CollectResult


class CollectorAgent(BaseAgent):
    name = "collector"
    system_prompt = COLLECTOR_SYSTEM

    async def run(self, input_data: dict[str, Any]) -> dict:
        """Run collection.

        input_data should contain:
            - target_product: str
            - competitors: list[str]
            - industry: str
            - focus_areas: list[str] (optional)
            - constraints: list[str] (optional, ratchet constraints from QA)
        """
        user_prompt = build_collector_prompt(
            target_product=input_data["target_product"],
            competitors=input_data.get("competitors", []),
            industry=input_data.get("industry", ""),
            focus_areas=input_data.get("focus_areas"),
        )

        # Inject ratchet constraints from previous QA feedback
        constraints = input_data.get("constraints", [])
        if constraints:
            user_prompt += "\n\nYou MUST satisfy these constraints:\n" + "\n".join(constraints)

        validated, llm_resp, traces = await self.call_and_validate(
            user_prompt=user_prompt,
            output_schema=CollectResult,
        )

        # Convert sources to dicts with IDs for downstream use
        sources = [s.model_dump() for s in validated.sources]

        return {
            "sources": sources,
            "traces": [t.model_dump() for t in traces],
            "_llm_response": {
                "input_tokens": llm_resp.input_tokens,
                "output_tokens": llm_resp.output_tokens,
                "duration": llm_resp.duration,
            },
        }
