"""Collector Agent — gathers competitive intelligence from multiple source types.

When a SearchProvider is configured, the agent first performs real web searches
for each product, then passes the results to the LLM for structured extraction.
Otherwise, falls back to LLM-only generation (original behavior).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.agents.base import BaseAgent
from app.llm.prompts import COLLECTOR_SYSTEM, build_collector_prompt
from app.schemas.base import CollectResult
from app.services.search import SearchResult, get_search_provider

logger = logging.getLogger(__name__)


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
        target_product = input_data["target_product"]
        competitors = input_data.get("competitors", [])
        industry = input_data.get("industry", "")
        focus_areas = input_data.get("focus_areas")

        # Attempt real web search
        search_results = await self._search_products(
            target_product, competitors, industry
        )

        # Build prompt — with or without search data
        if search_results:
            user_prompt = build_collector_prompt(
                target_product=target_product,
                competitors=competitors,
                industry=industry,
                focus_areas=focus_areas,
                search_results=search_results,
            )
        else:
            user_prompt = build_collector_prompt(
                target_product=target_product,
                competitors=competitors,
                industry=industry,
                focus_areas=focus_areas,
            )

        # Inject ratchet constraints from previous QA feedback
        constraints = input_data.get("constraints", [])
        if constraints:
            user_prompt += "\n\nYou MUST satisfy these constraints:\n" + "\n".join(
                constraints
            )

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

    async def _search_products(
        self,
        target_product: str,
        competitors: list[str],
        industry: str,
    ) -> list[SearchResult]:
        """Perform web searches for each product if a search provider is available."""
        provider = get_search_provider()
        if provider is None:
            return []

        all_results: list[SearchResult] = []
        queries = self._build_search_queries(target_product, competitors, industry)

        for query in queries:
            try:
                results = await provider.search(query)
                all_results.extend(results)
                logger.info(
                    "Search returned %d results for query: %s",
                    len(results),
                    query,
                )
            except Exception:
                logger.warning("Search failed for query: %s", query, exc_info=True)

        # Deduplicate by URL
        seen_urls: set[str] = set()
        unique_results: list[SearchResult] = []
        for r in all_results:
            if r.url and r.url not in seen_urls:
                seen_urls.add(r.url)
                unique_results.append(r)

        return unique_results

    @staticmethod
    def _build_search_queries(
        target_product: str,
        competitors: list[str],
        industry: str,
    ) -> list[str]:
        """Construct search queries for each product."""
        queries: list[str] = []
        industry_part = f" {industry}" if industry else ""

        # Main product query
        queries.append(f"{target_product}{industry_part} features pricing review")

        # Head-to-head comparisons
        for comp in competitors[:3]:  # limit to 3 competitors for search
            queries.append(f"{target_product} vs {comp} comparison")

        # Industry-level query if industry specified
        if industry:
            queries.append(
                f"best {industry} tools {target_product} {' '.join(competitors[:3])}"
            )

        return queries
