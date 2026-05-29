"""Pluggable search backends for the Collector Agent.

Supports:
- Tavily (AI-native, async, returns content directly) — SEARCH_PROVIDER=tavily
- DuckDuckGo via ddgs (free, no API key) — SEARCH_PROVIDER=ddgs
- None (disable search, LLM-only) — SEARCH_PROVIDER=none
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared data class
# ---------------------------------------------------------------------------

@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    content: str | None = None  # full page content (Tavily provides directly)


# ---------------------------------------------------------------------------
# Provider protocol
# ---------------------------------------------------------------------------

@runtime_checkable
class SearchProvider(Protocol):
    async def search(
        self, query: str, max_results: int | None = None
    ) -> list[SearchResult]: ...


# ---------------------------------------------------------------------------
# Tavily provider
# ---------------------------------------------------------------------------

class TavilySearchProvider:
    """Search via Tavily API — AI-native, async, returns content directly."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def search(
        self, query: str, max_results: int | None = None
    ) -> list[SearchResult]:
        max_results = max_results or settings.SEARCH_MAX_RESULTS
        try:
            from tavily import AsyncTavilyClient

            async with AsyncTavilyClient(api_key=self._api_key) as client:
                response = await client.search(
                    query,
                    max_results=max_results,
                    search_depth="advanced",
                    include_raw_content=False,
                )
            results: list[SearchResult] = []
            for r in response.get("results", []):
                results.append(
                    SearchResult(
                        title=r.get("title", ""),
                        url=r.get("url", ""),
                        snippet=r.get("content", "")[:300],
                        content=r.get("content"),
                    )
                )
            return results
        except Exception:
            logger.warning("Tavily search failed for query: %s", query, exc_info=True)
            return []


# ---------------------------------------------------------------------------
# DuckDuckGo provider (via ddgs)
# ---------------------------------------------------------------------------

class DDGSSearchProvider:
    """Search via DuckDuckGo (ddgs) — free, no API key needed.

    Returns snippets only; optionally fetches page content via httpx+BS4.
    """

    def __init__(self, fetch_content: bool | None = None) -> None:
        self._fetch_content = (
            fetch_content if fetch_content is not None
            else settings.SEARCH_FETCH_CONTENT
        )

    async def search(
        self, query: str, max_results: int | None = None
    ) -> list[SearchResult]:
        max_results = max_results or settings.SEARCH_MAX_RESULTS
        try:
            from ddgs import DDGS

            ddgs = DDGS()
            # ddgs is synchronous — run in thread to avoid blocking event loop
            raw_results = await asyncio.to_thread(
                ddgs.text, query, max_results=max_results
            )
        except Exception:
            logger.warning("DDGS search failed for query: %s", query, exc_info=True)
            return []

        results: list[SearchResult] = []
        for r in raw_results:
            sr = SearchResult(
                title=r.get("title", ""),
                url=r.get("href", ""),
                snippet=r.get("body", "")[:300],
            )
            results.append(sr)

        # Optionally fetch page content for top results
        if self._fetch_content and results:
            await self._fetch_contents(results[:5])

        return results

    async def _fetch_contents(self, results: list[SearchResult]) -> None:
        """Fetch and extract text content for a list of search results."""
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            logger.debug("beautifulsoup4 not installed, skipping content fetch")
            return

        async with httpx.AsyncClient(
            timeout=15.0, follow_redirects=True, headers={
                "User-Agent": "Mozilla/5.0 (compatible; Competa/0.1)"
            }
        ) as client:
            tasks = [self._fetch_one(client, r) for r in results]
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _fetch_one(
        self, client: httpx.AsyncClient, result: SearchResult
    ) -> None:
        """Fetch a single page and extract text content."""
        if not result.url:
            return
        try:
            from bs4 import BeautifulSoup

            resp = await client.get(result.url)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            # Remove script/style elements
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()

            text = soup.get_text(separator="\n", strip=True)
            # Truncate to reasonable size
            result.content = text[:3000] if len(text) > 3000 else text
        except Exception:
            logger.debug("Failed to fetch content from %s", result.url, exc_info=True)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_provider_instance: SearchProvider | None | str = "uninitialized"


def get_search_provider() -> SearchProvider | None:
    """Get or create the singleton search provider based on settings."""
    global _provider_instance
    if _provider_instance != "uninitialized":
        return _provider_instance if _provider_instance is not None else None

    provider_name = settings.SEARCH_PROVIDER.lower()

    if provider_name == "tavily":
        if not settings.TAVILY_API_KEY:
            logger.warning(
                "SEARCH_PROVIDER=tavily but TAVILY_API_KEY is empty — disabling search"
            )
            _provider_instance = None
        else:
            _provider_instance = TavilySearchProvider(api_key=settings.TAVILY_API_KEY)
            logger.info("Search provider: Tavily")
    elif provider_name == "ddgs":
        _provider_instance = DDGSSearchProvider()
        logger.info("Search provider: DuckDuckGo (ddgs)")
    else:
        _provider_instance = None
        logger.info("Search provider: none (LLM-only mode)")

    return _provider_instance


def reset_search_provider() -> None:
    """Reset the singleton — useful for testing."""
    global _provider_instance
    _provider_instance = "uninitialized"
