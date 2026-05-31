"""Collector Agent — gathers competitive intelligence from multiple source types.

When a SearchProvider is configured, the agent first performs real web searches
for each product, then passes the results to the LLM for structured extraction.
Otherwise, falls back to LLM-only generation (original behavior).
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from app.agents.base import BaseAgent
from app.llm.prompts import COLLECTOR_SYSTEM, build_collector_prompt
from app.schemas.base import CollectResult
from app.services.search import SearchResult, fetch_webpages, get_search_provider

logger = logging.getLogger(__name__)


class CollectorAgent(BaseAgent):
    name = "collector"
    system_prompt = COLLECTOR_SYSTEM

    async def run(self, input_data: dict[str, Any]) -> dict:
        """Run collection.

        input_data should contain:
            - target_product: str
            - competitors: list[str | dict]  (plain name or structured object)
            - industry: str
            - focus_areas: list[str] (optional)
            - constraints: list[str] (optional, ratchet constraints from QA)
            - our_product_notes: str (optional)
        """
        target_product = input_data["target_product"]
        raw_competitors = input_data.get("competitors", [])
        industry = input_data.get("industry", "")
        focus_areas = input_data.get("focus_areas")
        our_product_notes = input_data.get("our_product_notes", "")

        # Normalize competitors: str → {"name": str}, dict → pass through
        competitors: list[dict[str, Any]] = []
        for c in raw_competitors:
            if isinstance(c, str):
                competitors.append({"name": c, "category": "direct"})
            elif isinstance(c, dict):
                competitors.append(c)

        competitor_names = [c.get("name", str(c)) for c in competitors]
        competitor_websites = [c.get("website") for c in competitors if c.get("website")]

        # Attempt real web search
        search_results = await self._search_products(
            target_product, competitor_names, industry
        )

        # Deep-fetch competitor websites for richer content
        if competitor_websites:
            website_results = await self._fetch_competitor_websites(competitor_websites)
            search_results = website_results + search_results

        # Deep-fetch top search result URLs for richer content (beyond snippets)
        if search_results:
            search_results = await self._deep_fetch_top_results(search_results)

        # Inject ratchet constraints from previous QA feedback
        constraints = input_data.get("constraints", [])
        if constraints:
            # On retry, run supplementary searches based on constraint hints
            supp_results = await self._supplementary_search_from_constraints(
                constraints, target_product, competitor_names, industry
            )
            if supp_results:
                search_results = (search_results or []) + supp_results

        # Build prompt — with or without search data (AFTER supplementary search)
        if search_results:
            user_prompt = build_collector_prompt(
                target_product=target_product,
                competitors=competitors,
                industry=industry,
                focus_areas=focus_areas,
                search_results=search_results,
                our_product_notes=our_product_notes,
            )
        else:
            user_prompt = build_collector_prompt(
                target_product=target_product,
                competitors=competitors,
                industry=industry,
                focus_areas=focus_areas,
                our_product_notes=our_product_notes,
            )

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

        queries = self._build_search_queries(target_product, competitors, industry)

        # Run all queries in parallel for speed
        async def _safe_search(query: str) -> list[SearchResult]:
            try:
                results = await provider.search(query)
                logger.info(
                    "Search returned %d results for query: %s",
                    len(results),
                    query,
                )
                return results
            except Exception:
                logger.warning("Search failed for query: %s", query, exc_info=True)
                return []

        batch_results = await asyncio.gather(
            *[_safe_search(q) for q in queries],
            return_exceptions=False,
        )

        all_results: list[SearchResult] = []
        for results in batch_results:
            all_results.extend(results)

        # Deduplicate by URL
        seen_urls: set[str] = set()
        unique_results: list[SearchResult] = []
        for r in all_results:
            if r.url and r.url not in seen_urls:
                seen_urls.add(r.url)
                unique_results.append(r)

        return unique_results

    @staticmethod
    async def _fetch_competitor_websites(
        websites: list[str],
    ) -> list[SearchResult]:
        """Deep-fetch competitor websites directly for content."""
        try:
            fetched = await fetch_webpages(websites, max_chars=8000)
        except Exception:
            logger.warning("Competitor website fetch failed", exc_info=True)
            return []

        results: list[SearchResult] = []
        for item in fetched:
            if not isinstance(item, dict) or not item.get("content"):
                continue
            results.append(SearchResult(
                title=item.get("title") or item.get("url", ""),
                url=item.get("url", ""),
                snippet=(item.get("content") or "")[:300],
                content=item.get("content"),
            ))
        return results

    @staticmethod
    async def _deep_fetch_top_results(
        results: list[SearchResult],
        top_n: int = 5,
    ) -> list[SearchResult]:
        """Deep-fetch full page content for the top search results.

        Only fetches URLs that don't already have content (i.e. DDGS results).
        Tavily results already include content.
        """
        # Filter to results that lack content and have a URL
        need_fetch = [r for r in results[:top_n] if not r.content and r.url]
        if not need_fetch:
            return results

        urls = [r.url for r in need_fetch]
        try:
            fetched = await fetch_webpages(urls, max_chars=8000)
        except Exception:
            logger.warning("Deep-fetch batch failed", exc_info=True)
            return results

        # Merge fetched content back into search results
        url_to_content: dict[str, str | None] = {}
        for item in fetched:
            if isinstance(item, dict):
                url_to_content[item.get("url", "")] = item.get("content")
        for r in need_fetch:
            content = url_to_content.get(r.url)
            if content:
                r.content = content
        return results

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

    async def _supplementary_search_from_constraints(
        self,
        constraints: list[str],
        target_product: str,
        competitor_names: list[str],
        industry: str,
    ) -> list[SearchResult]:
        """Run targeted supplementary searches based on QA constraint hints.

        Extracts keywords from constraint strings (e.g. "pricing", "features")
        and runs focused searches to fill the gaps.
        """
        provider = get_search_provider()
        if provider is None:
            return []

        # Extract likely search keywords from constraint descriptions
        supp_queries: list[str] = []
        for constraint in constraints:
            cl = constraint.lower()
            # Detect common gap areas and build targeted queries
            if "pricing" in cl or "price" in cl or "tier" in cl:
                for name in competitor_names[:3]:
                    supp_queries.append(f"{name} pricing plans tiers cost")
            if "feature" in cl or "capability" in cl:
                for name in competitor_names[:3]:
                    supp_queries.append(f"{name} features capabilities comparison")
            if "evidence" in cl or "source" in cl or "coverage" in cl:
                industry_part = f" {industry}" if industry else ""
                supp_queries.append(f"{target_product}{industry_part} competitive analysis review")
            if "swot" in cl or "strength" in cl or "weakness" in cl:
                for name in competitor_names[:2]:
                    supp_queries.append(f"{name} strengths weaknesses analysis")

        if not supp_queries:
            return []

        # Deduplicate queries
        supp_queries = list(dict.fromkeys(supp_queries))[:5]

        async def _safe_search(query: str) -> list[SearchResult]:
            try:
                return await provider.search(query)
            except Exception:
                logger.warning("Supplementary search failed for: %s", query, exc_info=True)
                return []

        batch_results = await asyncio.gather(
            *[_safe_search(q) for q in supp_queries],
            return_exceptions=False,
        )

        all_results: list[SearchResult] = []
        for results in batch_results:
            all_results.extend(results)

        # Deduplicate by URL
        seen_urls: set[str] = set()
        unique: list[SearchResult] = []
        for r in all_results:
            if r.url and r.url not in seen_urls:
                seen_urls.add(r.url)
                unique.append(r)

        if unique:
            logger.info("Supplementary search found %d new results", len(unique))
        return unique
