"""L3 Capability — Tool registry, search backends, and service integrations.

Re-exports:
  - get_search_provider: Pluggable search backend factory
  - fetch_webpage, fetch_webpages: Webpage content fetching
  - SearchResult: Search result dataclass
  - SearchProvider: Protocol for search backends
  - score_source_reliability: Source reliability scoring (0-1 scale)
"""
from app.services.search import (
    SearchResult,
    SearchProvider,
    get_search_provider,
    fetch_webpage,
    fetch_webpages,
)
from app.agents.collector import score_source_reliability

__all__ = [
    "SearchResult",
    "SearchProvider",
    "get_search_provider",
    "fetch_webpage",
    "fetch_webpages",
    "score_source_reliability",
]
