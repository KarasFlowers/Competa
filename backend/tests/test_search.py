"""Tests for the search service and Collector Agent search integration."""

import pytest

from app.services.search import (
    DDGSSearchProvider,
    SearchResult,
    TavilySearchProvider,
    get_search_provider,
    reset_search_provider,
)


PUBLIC_TEST_IP = "93.184.216.34"


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


class TestCollectorFallback:
    async def test_retries_without_page_content_when_provider_blocks(self, monkeypatch):
        from app.agents.collector import CollectorAgent
        from app.llm.client import LLMContentFilterError, LLMResponse
        from app.schemas.base import CollectResult, Source

        prompt_history: list[str] = []
        search_results = [
            SearchResult(
                title="Example Pricing",
                url="https://example.com/pricing",
                snippet="Pricing overview for Example product.",
                content="Raw fetched page content that may trigger provider blocks.",
            )
        ]

        async def fake_search_products(self, target_product, competitors, industry):
            return search_results

        async def fake_call_and_validate(self, user_prompt, output_schema, system_prompt=None):
            prompt_history.append(user_prompt)
            if "Content:" in user_prompt:
                raise RuntimeError("collector: blocked") from LLMContentFilterError(
                    "Your request was blocked."
                )
            return (
                CollectResult(
                    sources=[
                        Source(
                            type="url",
                            url="https://example.com/pricing",
                            title="Example Pricing",
                            content_snippet="Pricing overview for Example product.",
                        )
                    ],
                    coverage_note="ok",
                ),
                LLMResponse(
                    content="{}",
                    input_tokens=10,
                    output_tokens=5,
                    model="test-model",
                    duration=0.1,
                ),
                [],
            )

        monkeypatch.setattr(CollectorAgent, "_search_products", fake_search_products)
        monkeypatch.setattr(CollectorAgent, "call_and_validate", fake_call_and_validate)

        agent = CollectorAgent()
        result = await agent.run({
            "target_product": "Competa",
            "competitors": ["Example"],
            "industry": "SaaS",
        })

        assert len(prompt_history) == 2
        assert "Content:" in prompt_history[0]
        assert "Content:" not in prompt_history[1]
        assert "Snippet:" in prompt_history[1]
        assert result["sources"][0]["url"] == "https://example.com/pricing"


class TestUrlSafety:
    def test_blocks_unsafe_schemes_and_internal_hosts(self, monkeypatch):
        from app.services import search

        assert search._is_url_safe("ftp://example.com/file") is False
        assert search._is_url_safe("file:///etc/passwd") is False
        assert search._is_url_safe("https://localhost/admin") is False
        assert search._is_url_safe("https://example.local/page") is False

    def test_blocks_private_and_link_local_ip_literals(self):
        from app.services import search

        assert search._is_url_safe("http://10.0.0.1") is False
        assert search._is_url_safe("http://192.168.1.10") is False
        assert search._is_url_safe("http://169.254.169.254/latest/meta-data") is False
        assert search._is_url_safe("http://[::1]/") is False
        assert search._is_url_safe("http://[fe80::1]/") is False

    def test_blocks_dns_names_that_resolve_to_private_ips(self, monkeypatch):
        from app.services import search

        monkeypatch.setattr(
            search.socket,
            "getaddrinfo",
            lambda *args, **kwargs: [(search.socket.AF_INET, 0, 0, "", ("10.0.0.8", 0))],
        )

        assert search._is_url_safe("https://metadata.example.com") is False

    def test_allows_public_dns_resolution(self, monkeypatch):
        from app.services import search

        monkeypatch.setattr(
            search.socket,
            "getaddrinfo",
            lambda *args, **kwargs: [(search.socket.AF_INET, 0, 0, "", (PUBLIC_TEST_IP, 0))],
        )

        assert search._is_url_safe("https://example.com") is True

    async def test_safe_get_blocks_redirect_to_private_ip(self, monkeypatch):
        from app.services import search

        monkeypatch.setattr(
            search.socket,
            "getaddrinfo",
            lambda *args, **kwargs: [(search.socket.AF_INET, 0, 0, "", (PUBLIC_TEST_IP, 0))],
        )

        class _Resp:
            is_redirect = True
            headers = {"location": "http://169.254.169.254/latest/meta-data"}
            url = "https://example.com/start"
            status_code = 302
            text = ""

        class _Client:
            async def get(self, url):
                return _Resp()

        with pytest.raises(ValueError, match="Redirect blocked"):
            await search._safe_get(_Client(), "https://example.com/start")


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


class TestRobotsCompliance:
    """fetch_webpage must honor the target site's robots.txt (compliance)."""

    async def test_disallowed_url_is_skipped(self, monkeypatch):
        from app.services import search

        search.reset_robots_cache()
        monkeypatch.setattr(search.settings, "RESPECT_ROBOTS_TXT", True)
        monkeypatch.setattr(
            search.socket,
            "getaddrinfo",
            lambda *args, **kwargs: [(search.socket.AF_INET, 0, 0, "", (PUBLIC_TEST_IP, 0))],
        )

        class _Resp:
            status_code = 200
            text = "User-agent: *\nDisallow: /private"

        class _Client:
            def __init__(self, *a, **k): ...
            async def __aenter__(self): return self
            async def __aexit__(self, *a): return False
            async def get(self, url): return _Resp()

        monkeypatch.setattr(search.httpx, "AsyncClient", _Client)

        allowed = await search._is_fetch_allowed("https://example.com/private/page")
        assert allowed is False

        # A path outside the disallow rule is permitted
        search.reset_robots_cache()
        allowed_ok = await search._is_fetch_allowed("https://example.com/public/page")
        assert allowed_ok is True

    async def test_missing_robots_fails_open(self, monkeypatch):
        from app.services import search

        search.reset_robots_cache()
        monkeypatch.setattr(search.settings, "RESPECT_ROBOTS_TXT", True)
        monkeypatch.setattr(
            search.socket,
            "getaddrinfo",
            lambda *args, **kwargs: [(search.socket.AF_INET, 0, 0, "", (PUBLIC_TEST_IP, 0))],
        )

        class _Resp:
            status_code = 404
            text = ""

        class _Client:
            def __init__(self, *a, **k): ...
            async def __aenter__(self): return self
            async def __aexit__(self, *a): return False
            async def get(self, url): return _Resp()

        monkeypatch.setattr(search.httpx, "AsyncClient", _Client)
        assert await search._is_fetch_allowed("https://example.com/anything") is True

    async def test_disabled_setting_skips_check(self, monkeypatch):
        from app.services import search

        search.reset_robots_cache()
        monkeypatch.setattr(search.settings, "RESPECT_ROBOTS_TXT", False)
        # Should return True without any network call
        assert await search._is_fetch_allowed("https://example.com/private/x") is True


class TestSourceCuration:
    def test_curate_sources_deduplicates_and_caps_domains(self):
        from app.services.curation import curate_sources

        raw_sources = [
            {
                "id": "s1",
                "type": "url",
                "url": "https://example.com/pricing",
                "title": "Pricing",
                "content_snippet": "Official pricing page",
                "reliability_score": 0.9,
            },
            {
                "id": "s2",
                "type": "url",
                "url": "https://example.com/pricing?ref=ad",
                "title": "Pricing Duplicate",
                "content_snippet": "Official pricing page",
                "reliability_score": 0.91,
            },
            {
                "id": "s3",
                "type": "url",
                "url": "https://example.com/features",
                "title": "Features",
                "content_snippet": "Feature summary",
                "reliability_score": 0.88,
            },
            {
                "id": "s4",
                "type": "url",
                "url": "https://example.com/blog",
                "title": "Overflow Domain",
                "content_snippet": "extra",
                "reliability_score": 0.87,
            },
            {
                "id": "s5",
                "type": "url",
                "url": "https://unknown-blog.net/post",
                "title": "Low reliability",
                "content_snippet": "weak source",
                "reliability_score": 0.42,
            },
            {
                "id": "s6",
                "type": "survey",
                "title": "[模拟] Survey",
                "content_snippet": "Primary research insight",
                "reliability_score": 0.55,
            },
        ]

        result = curate_sources(raw_sources, max_sources=10, max_sources_per_domain=2)
        kept_ids = [item["id"] for item in result.sources]

        assert "s6" in kept_ids  # first-party evidence preserved
        assert "s5" not in kept_ids  # low reliability url removed
        assert "s2" not in kept_ids  # normalized duplicate removed
        assert "s4" not in kept_ids  # domain cap applied
        assert result.summary["removed_count"] == 3
        assert result.summary["removed_reasons"]["duplicate_url"] == 1
        assert result.summary["removed_reasons"]["low_reliability"] == 1
        assert result.summary["removed_reasons"]["domain_cap"] == 1

    def test_curated_sources_include_excerpt_and_tags(self):
        from app.services.curation import curate_sources

        result = curate_sources([
            {
                "id": "s1",
                "type": "url",
                "url": "https://official-site.com/product",
                "title": "Official Product Page",
                "content_snippet": "The platform offers automation, analytics, and collaboration features for enterprise teams.",
                "reliability_score": 0.9,
            },
        ])

        curated = result.sources[0]
        assert curated["curated_excerpt"].startswith("Official Product Page:")
        assert "high_confidence" in curated["curation_tags"]
