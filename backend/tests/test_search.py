"""Tests for the search service and Collector Agent search integration."""

import pytest

from app.services.search import (
    DDGSSearchProvider,
    SearchResult,
    TavilySearchProvider,
    get_search_provider,
    reset_search_provider,
)


# ---------------------------------------------------------------------------
# SearchResult dataclass
# ---------------------------------------------------------------------------

class TestSearchResult:
    def test_defaults(self):
        sr = SearchResult(title="T", url="https://example.com", snippet="S")
        assert sr.content is None

    def test_with_content(self):
        sr = SearchResult(title="T", url="U", snippet="S", content="Full text")
        assert sr.content == "Full text"


# ---------------------------------------------------------------------------
# TavilySearchProvider (mocked)
# ---------------------------------------------------------------------------

class TestTavilySearchProvider:
    async def test_search_returns_results(self, monkeypatch):
        fake_response = {
            "results": [
                {
                    "title": "Product A Review",
                    "url": "https://example.com/a",
                    "content": "Product A is great for teams.",
                },
                {
                    "title": "Product B Pricing",
                    "url": "https://example.com/b",
                    "content": "Product B costs $10/mo.",
                },
            ]
        }

        class FakeAsyncClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def search(self, query, **kwargs):
                return fake_response

        monkeypatch.setattr("tavily.AsyncTavilyClient", lambda **kw: FakeAsyncClient())
        provider = TavilySearchProvider(api_key="test-key")
        results = await provider.search("Product A vs Product B")
        assert len(results) == 2
        assert results[0].title == "Product A Review"
        assert results[0].content is not None

    async def test_search_graceful_failure(self, monkeypatch):
        class BrokenClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def search(self, query, **kwargs):
                raise RuntimeError("API down")

        monkeypatch.setattr("tavily.AsyncTavilyClient", lambda **kw: BrokenClient())
        provider = TavilySearchProvider(api_key="test-key")
        results = await provider.search("should fail gracefully")
        assert results == []


# ---------------------------------------------------------------------------
# DDGSSearchProvider (mocked)
# ---------------------------------------------------------------------------

class TestDDGSSearchProvider:
    async def test_search_returns_results(self, monkeypatch):
        fake_ddgs_results = [
            {"title": "Result 1", "href": "https://example.com/1", "body": "Snippet 1"},
            {"title": "Result 2", "href": "https://example.com/2", "body": "Snippet 2"},
        ]

        monkeypatch.setattr(
            "app.services.search.asyncio.to_thread",
            lambda fn, *args, **kwargs: _fake_to_thread(fn, fake_ddgs_results),
        )
        # Disable content fetching for this test
        provider = DDGSSearchProvider(fetch_content=False)
        results = await provider.search("test query")
        assert len(results) == 2
        assert results[0].url == "https://example.com/1"

    async def test_search_graceful_failure(self, monkeypatch):
        async def _failing_to_thread(fn, *args, **kwargs):
            raise RuntimeError("DDGS down")

        monkeypatch.setattr("app.services.search.asyncio.to_thread", _failing_to_thread)
        provider = DDGSSearchProvider(fetch_content=False)
        results = await provider.search("should fail gracefully")
        assert results == []


async def _fake_to_thread(fn, return_value):
    """Helper to mock asyncio.to_thread for DDGS."""
    return return_value


# ---------------------------------------------------------------------------
# Factory / get_search_provider
# ---------------------------------------------------------------------------

class TestGetSearchProvider:
    def setup_method(self):
        reset_search_provider()

    def teardown_method(self):
        reset_search_provider()

    def test_none_provider(self, monkeypatch):
        monkeypatch.setattr("app.services.search.settings.SEARCH_PROVIDER", "none")
        provider = get_search_provider()
        assert provider is None

    def test_ddgs_provider(self, monkeypatch):
        monkeypatch.setattr("app.services.search.settings.SEARCH_PROVIDER", "ddgs")
        provider = get_search_provider()
        assert isinstance(provider, DDGSSearchProvider)

    def test_tavily_provider(self, monkeypatch):
        monkeypatch.setattr("app.services.search.settings.SEARCH_PROVIDER", "tavily")
        monkeypatch.setattr("app.services.search.settings.TAVILY_API_KEY", "tvly-test")
        provider = get_search_provider()
        assert isinstance(provider, TavilySearchProvider)

    def test_tavily_without_key_falls_back(self, monkeypatch):
        monkeypatch.setattr("app.services.search.settings.SEARCH_PROVIDER", "tavily")
        monkeypatch.setattr("app.services.search.settings.TAVILY_API_KEY", "")
        provider = get_search_provider()
        assert provider is None

    def test_singleton(self, monkeypatch):
        monkeypatch.setattr("app.services.search.settings.SEARCH_PROVIDER", "ddgs")
        p1 = get_search_provider()
        p2 = get_search_provider()
        assert p1 is p2


# ---------------------------------------------------------------------------
# Collector Agent search query construction
# ---------------------------------------------------------------------------

class TestCollectorSearchQueries:
    def test_basic_queries(self):
        from app.agents.collector import CollectorAgent

        queries = CollectorAgent._build_search_queries(
            target_product="Slack",
            competitors=["Teams", "Discord"],
            industry="SaaS",
        )
        assert len(queries) == 4  # 1 main + 2 comparisons + 1 industry
        assert "Slack" in queries[0]
        assert "Slack vs Teams" in queries[1]
        assert "Slack vs Discord" in queries[2]
        assert "SaaS" in queries[3]

    def test_no_industry(self):
        from app.agents.collector import CollectorAgent

        queries = CollectorAgent._build_search_queries(
            target_product="Slack",
            competitors=["Teams"],
            industry="",
        )
        assert len(queries) == 2  # 1 main + 1 comparison, no industry query

    def test_many_competitors_capped(self):
        from app.agents.collector import CollectorAgent

        queries = CollectorAgent._build_search_queries(
            target_product="Slack",
            competitors=["A", "B", "C", "D", "E"],
            industry="SaaS",
        )
        # 1 main + 3 comparisons (capped) + 1 industry = 5
        assert len(queries) == 5


# ---------------------------------------------------------------------------
# _find_claim_recursive (from tasks.py)
# ---------------------------------------------------------------------------

class TestFindClaimRecursive:
    def test_top_level_claim(self):
        from app.api.tasks import _find_claim_recursive

        sections = [
            {"claims": [{"id": "c1", "content": "old"}], "subsections": []},
        ]
        claim = _find_claim_recursive(sections, "c1")
        assert claim is not None
        assert claim["content"] == "old"

    def test_nested_subsection_claim(self):
        from app.api.tasks import _find_claim_recursive

        sections = [
            {
                "claims": [{"id": "c1", "content": "top"}],
                "subsections": [
                    {
                        "claims": [{"id": "c2", "content": "nested"}],
                        "subsections": [],
                    },
                ],
            },
        ]
        claim = _find_claim_recursive(sections, "c2")
        assert claim is not None
        assert claim["content"] == "nested"

    def test_deeply_nested_claim(self):
        from app.api.tasks import _find_claim_recursive

        sections = [
            {
                "claims": [],
                "subsections": [
                    {
                        "claims": [],
                        "subsections": [
                            {
                                "claims": [{"id": "c3", "content": "deep"}],
                                "subsections": [],
                            },
                        ],
                    },
                ],
            },
        ]
        claim = _find_claim_recursive(sections, "c3")
        assert claim is not None
        assert claim["content"] == "deep"

    def test_not_found(self):
        from app.api.tasks import _find_claim_recursive

        sections = [{"claims": [{"id": "c1", "content": "x"}], "subsections": []}]
        claim = _find_claim_recursive(sections, "nonexistent")
        assert claim is None

    def test_empty_sections(self):
        from app.api.tasks import _find_claim_recursive

        claim = _find_claim_recursive([], "any")
        assert claim is None
