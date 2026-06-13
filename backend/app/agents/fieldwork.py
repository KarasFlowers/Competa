"""Fieldwork Agent — simulates running the designed survey + interview.

Turns the survey questionnaire and interview guide (design artifacts) into
synthetic-but-realistic research results grounded in the personas, so the
findings flow back into the evidence pool for the Analyst. Results are clearly
flagged as simulated (reliability_score reflects this).
"""

from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent
from app.llm.prompts import FIELDWORK_SYSTEM, build_fieldwork_prompt
from app.schemas.survey import FieldworkOutput


class FieldworkAgent(BaseAgent):
    name = "fieldwork"
    system_prompt = FIELDWORK_SYSTEM

    async def run(self, input_data: dict[str, Any]) -> dict:
        """Run simulated fieldwork.

        input_data should contain:
            - target_product: str
            - competitors: list[str]
            - survey: dict (SurveyOutput, optional)
            - interview: dict (InterviewGuideOutput, optional)
            - personas: list[dict] (from analysis, optional)
            - our_product_notes: str (optional)
        """
        target_product = input_data.get("target_product", "")
        competitors = input_data.get("competitors", [])
        survey = input_data.get("survey") or {}
        interview = input_data.get("interview") or {}
        personas = input_data.get("personas") or []
        our_product_notes = input_data.get("our_product_notes", "")
        output_language = input_data.get("output_language", "zh")

        competitor_names = [
            c.get("name", str(c)) if isinstance(c, dict) else c
            for c in competitors
        ]

        user_prompt = build_fieldwork_prompt(
            target_product=target_product,
            competitors=competitor_names,
            survey=survey,
            interview=interview,
            personas=personas,
            our_product_notes=our_product_notes,
        )

        validated, llm_resp, traces = await self.call_and_validate(
            user_prompt=user_prompt,
            output_schema=FieldworkOutput,
            output_language=output_language,
        )

        fieldwork = validated.model_dump()
        sources = self._build_sources(fieldwork)

        return {
            "fieldwork": fieldwork,
            "sources": sources,
            "traces": [t.model_dump() for t in traces],
            "_llm_response": {
                "input_tokens": llm_resp.input_tokens,
                "output_tokens": llm_resp.output_tokens,
                "duration": llm_resp.duration,
            },
        }

    @staticmethod
    def _build_sources(fieldwork: dict[str, Any]) -> list[dict[str, Any]]:
        """Convert simulated fieldwork into evidence sources for the Analyst.

        Survey result sets → SURVEY sources; interview transcripts → INTERVIEW
        sources. Reliability mirrors the Collector's type-based scoring and is
        kept modest (0.5/0.55) because the data is synthetic, not field-collected.
        Titles are prefixed with [模拟] so they are never mistaken for real studies.
        """
        import uuid

        sources: list[dict[str, Any]] = []

        for rs in fieldwork.get("survey_results", []):
            persona = rs.get("persona", "用户群体")
            n = rs.get("respondent_count", 0)
            findings = rs.get("key_findings", [])
            answer_lines = [
                f"[{a.get('dimension', 'general')}] {a.get('answer', '')}"
                for a in rs.get("answers", [])
                if a.get("answer")
            ]
            snippet_parts = []
            if findings:
                snippet_parts.append("核心发现: " + "; ".join(findings))
            if answer_lines:
                snippet_parts.append("应答摘要: " + " | ".join(answer_lines[:6]))
            snippet = "\n".join(snippet_parts) or "（无应答数据）"
            sources.append({
                "id": uuid.uuid4().hex,
                "type": "survey",
                "url": None,
                "title": f"[模拟] 问卷调研结果 · {persona}（N≈{n}）",
                "content_snippet": snippet[:1000],
                "reliability_score": 0.55,
            })

        for tr in fieldwork.get("interview_transcripts", []):
            persona = tr.get("persona", "受访者")
            findings = tr.get("key_findings", [])
            quote_lines = [
                f"“{e.get('quote', '')}” — {e.get('insight', '')}"
                for e in tr.get("excerpts", [])
                if e.get("quote")
            ]
            snippet_parts = []
            if findings:
                snippet_parts.append("核心洞察: " + "; ".join(findings))
            if quote_lines:
                snippet_parts.append("访谈摘录:\n" + "\n".join(quote_lines[:5]))
            snippet = "\n".join(snippet_parts) or "（无访谈记录）"
            sources.append({
                "id": uuid.uuid4().hex,
                "type": "interview",
                "url": None,
                "title": f"[模拟] 用户访谈记录 · {persona}",
                "content_snippet": snippet[:1000],
                "reliability_score": 0.6,
            })

        return sources
