"""Interview Agent — designs semi-structured interview guides for competitive analysis."""

from __future__ import annotations

import json
from typing import Any

from app.agents.base import BaseAgent
from app.llm.prompts import INTERVIEW_SYSTEM, build_interview_prompt
from app.schemas.survey import InterviewGuideOutput


class InterviewAgent(BaseAgent):
    name = "interview"
    system_prompt = INTERVIEW_SYSTEM

    async def run(self, input_data: dict[str, Any]) -> dict:
        """Run interview guide design.

        input_data should contain:
            - target_product: str
            - competitors: list[str]
            - industry: str (optional)
            - personas: list[dict] (optional, from analysis)
        """
        target_product = input_data.get("target_product", "")
        competitors = input_data.get("competitors", [])
        industry = input_data.get("industry", "")
        personas = input_data.get("personas")

        # Normalize competitor names
        competitor_names = [
            c.get("name", str(c)) if isinstance(c, dict) else c
            for c in competitors
        ]

        user_prompt = build_interview_prompt(
            target_product=target_product,
            competitors=competitor_names,
            industry=industry,
            personas=personas,
        )

        validated, llm_resp, traces = await self.call_and_validate(
            user_prompt=user_prompt,
            output_schema=InterviewGuideOutput,
        )

        return {
            "interview": validated.model_dump(),
            "traces": [t.model_dump() for t in traces],
            "_llm_response": {
                "input_tokens": llm_resp.input_tokens,
                "output_tokens": llm_resp.output_tokens,
                "duration": llm_resp.duration,
            },
        }
