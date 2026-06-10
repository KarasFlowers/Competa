"""Pluggable search backends for the Collector Agent.

Supports:
- Tavily (AI-native, async, returns content directly) — SEARCH_PROVIDER=tavily
- DuckDuckGo via ddgs (free, no API key) — SEARCH_PROVIDER=ddgs
- Bing via scraping cn.bing.com (free, no API key, China-accessible) — SEARCH_PROVIDER=bing
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
# Bing provider (scraping cn.bing.com — works in China, no API key)
# ---------------------------------------------------------------------------

class BingSearchProvider:
    """Search via Bing (cn.bing.com) — free, China-accessible, no API key.

    Scrapes the HTML search results page. Rate-limited to avoid being blocked.
    """

    _SEARCH_URL = "https://cn.bing.com/search"

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
            from bs4 import BeautifulSoup

            async with httpx.AsyncClient(
                timeout=15.0,
                follow_redirects=True,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                },
            ) as client:
                resp = await client.get(
                    self._SEARCH_URL,
                    params={"q": query, "count": str(min(max_results, 15))},
                )
                resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")
            results: list[SearchResult] = []

            # Bing result blocks: <li class="b_algo">
            for item in soup.select("li.b_algo"):
                if len(results) >= max_results:
                    break
                title_el = item.select_one("h2 a")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                url = title_el.get("href", "")
                snippet_el = item.select_one(".b_caption p, .b_lineclamp2")
                snippet = snippet_el.get_text(strip=True) if snippet_el else ""
                if title and url:
                    results.append(SearchResult(title=title, url=url, snippet=snippet[:300]))

            # Optionally fetch full content for top results
            if self._fetch_content and results:
                await self._fetch_contents(results[:5])

            return results

        except Exception:
            logger.warning("Bing search failed for query: %s", query, exc_info=True)
            return []

    async def _fetch_contents(self, results: list[SearchResult]) -> None:
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            return

        async with httpx.AsyncClient(
            timeout=15.0, follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; Competa/0.1)"},
        ) as client:
            tasks = [self._fetch_one(client, r) for r in results]
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _fetch_one(
        self, client: httpx.AsyncClient, result: SearchResult
    ) -> None:
        if not result.url:
            return
        try:
            from bs4 import BeautifulSoup

            resp = await client.get(result.url)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            text = soup.get_text(separator="\n", strip=True)
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
    elif provider_name == "bing":
        _provider_instance = BingSearchProvider()
        logger.info("Search provider: Bing (cn.bing.com)")
    else:
        _provider_instance = None
        logger.info("Search provider: none (LLM-only mode)")

    return _provider_instance


def reset_search_provider() -> None:
    """Reset the singleton — useful for testing."""
    global _provider_instance
    _provider_instance = "uninitialized"


# ---------------------------------------------------------------------------
# Standalone webpage fetcher (for deep-fetching specific URLs)
# ---------------------------------------------------------------------------

# Internal network / unsafe URL patterns to block
_BLOCKED_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}
_BLOCKED_SCHEMES = {"file", "ftp"}

# Cache parsed robots.txt rules per host to avoid refetching
_ROBOTS_CACHE: dict[str, object] = {}
_ROBOTS_USER_AGENT = "Competa"


def _is_url_safe(url: str) -> bool:
    """Reject internal / unsafe URLs to prevent SSRF."""
    from urllib.parse import urlparse

    try:
        parsed = urlparse(url)
    except Exception:
        return False
    if parsed.scheme in _BLOCKED_SCHEMES:
        return False
    if parsed.hostname in _BLOCKED_HOSTS:
        return False
    if parsed.hostname and parsed.hostname.endswith(".local"):
        return False
    return True


async def _is_fetch_allowed(url: str) -> bool:
    """Check the target site's robots.txt before fetching (compliance).

    Fails open (returns True) when robots.txt is missing or unreachable —
    standard crawler behavior. Caches the parser per host. Controlled by the
    RESPECT_ROBOTS_TXT setting (default on).
    """
    if not getattr(settings, "RESPECT_ROBOTS_TXT", True):
        return True

    from urllib.parse import urlparse
    from urllib.robotparser import RobotFileParser

    try:
        parsed = urlparse(url)
    except Exception:
        return True
    host = parsed.hostname or ""
    if not host:
        return True

    cache_key = f"{parsed.scheme}://{parsed.netloc}"
    parser = _ROBOTS_CACHE.get(cache_key)
    if parser is None:
        parser = RobotFileParser()
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        try:
            async with httpx.AsyncClient(
                timeout=8.0, follow_redirects=True,
                headers={"User-Agent": f"{_ROBOTS_USER_AGENT}/0.1"},
            ) as client:
                resp = await client.get(robots_url)
            if resp.status_code >= 400:
                # No robots.txt (or forbidden) → allowed by convention
                parser.parse([])
            else:
                parser.parse(resp.text.splitlines())
        except Exception:
            logger.debug("robots.txt fetch failed for %s; allowing", host, exc_info=True)
            parser.parse([])
        _ROBOTS_CACHE[cache_key] = parser

    try:
        allowed = parser.can_fetch(_ROBOTS_USER_AGENT, url)
        if not allowed:
            logger.info("robots.txt disallows fetching %s — skipping", url)
        return allowed
    except Exception:
        return True


def reset_robots_cache() -> None:
    """Clear the robots.txt parser cache — useful for testing."""
    _ROBOTS_CACHE.clear()


async def fetch_webpage(
    url: str,
    *,
    max_chars: int = 8000,
    timeout: float = 20.0,
) -> dict[str, str | None]:
    """Fetch a single URL and return cleaned text content.

    Returns dict with keys: url, title, content (or None on failure).
    Raises ValueError if URL is unsafe.
    """
    if not _is_url_safe(url):
        raise ValueError(f"URL blocked (internal/unsafe): {url}")

    # Respect the target site's robots.txt before fetching
    if not await _is_fetch_allowed(url):
        logger.info("Skipping %s — disallowed by robots.txt", url)
        return {"url": url, "title": None, "content": None}

    try:
        from bs4 import BeautifulSoup
    except ImportError:
        logger.warning("beautifulsoup4 not installed; cannot fetch webpage content")
        return {"url": url, "title": None, "content": None}

    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; Competa/0.1)"},
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        # Extract title
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else url

        # Remove noise elements
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "iframe"]):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)
        # Truncate to max_chars
        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n[Content truncated]"

        return {"url": url, "title": title, "content": text}

    except Exception:
        logger.warning("Failed to fetch webpage: %s", url, exc_info=True)
        return {"url": url, "title": None, "content": None}


async def fetch_webpages(
    urls: list[str],
    *,
    max_chars: int = 8000,
    timeout: float = 20.0,
) -> list[dict[str, str | None]]:
    """Fetch multiple URLs in parallel and return results."""
    tasks = [fetch_webpage(u, max_chars=max_chars, timeout=timeout) for u in urls]
    return await asyncio.gather(*tasks, return_exceptions=False)
