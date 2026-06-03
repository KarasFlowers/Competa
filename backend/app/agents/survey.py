"""Survey Agent — designs structured questionnaires for competitive analysis research."""

from __future__ import annotations

import json
from typing import Any

from app.agents.base import BaseAgent
from app.llm.prompts import SURVEY_SYSTEM, build_survey_prompt
from app.schemas.survey import SurveyOutput


class SurveyAgent(BaseAgent):
    name = "survey"
    system_prompt = SURVEY_SYSTEM

    async def run(self, input_data: dict[str, Any]) -> dict:
        """Run survey design.

        input_data should contain:
            - target_product: str
            - competitors: list[str]
            - industry: str (optional)
            - focus_areas: list[str] (optional)
        """
        target_product = input_data.get("target_product", "")
        competitors = input_data.get("competitors", [])
        industry = input_data.get("industry", "")
        focus_areas = input_data.get("focus_areas")

        # Normalize competitor names
        competitor_names = [
            c.get("name", str(c)) if isinstance(c, dict) else c
            for c in competitors
        ]

        user_prompt = build_survey_prompt(
            target_product=target_product,
            competitors=competitor_names,
            industry=industry,
            focus_areas=focus_areas,
        )

        validated, llm_resp, traces = await self.call_and_validate(
            user_prompt=user_prompt,
            output_schema=SurveyOutput,
        )

        return {
            "survey": validated.model_dump(),
            "traces": [t.model_dump() for t in traces],
            "_llm_response": {
                "input_tokens": llm_resp.input_tokens,
                "output_tokens": llm_resp.output_tokens,
                "duration": llm_resp.duration,
            },
        }
