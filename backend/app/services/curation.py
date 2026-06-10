"""Deterministic evidence curation utilities for source quality control."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse


FIRST_PARTY_SOURCE_TYPES = {"survey", "interview"}
MAX_SOURCES_PER_DOMAIN = 2
MAX_CURATED_SOURCES = 12
MIN_RELIABILITY_SCORE = 0.58
MAX_SNIPPET_LENGTH = 320


@dataclass(slots=True)
class CuratedSourcesResult:
    sources: list[dict[str, Any]]
    all_sources: list[dict[str, Any]]
    removed_count: int
    summary: dict[str, Any]


def curate_sources(
    sources: list[dict[str, Any]],
    *,
    max_sources: int = MAX_CURATED_SOURCES,
    max_sources_per_domain: int = MAX_SOURCES_PER_DOMAIN,
    min_reliability_score: float = MIN_RELIABILITY_SCORE,
) -> CuratedSourcesResult:
    """Deduplicate and prioritize sources before analysis.

    Strategy:
      - Keep first-party human research (`survey` / `interview`) regardless of score.
      - Normalize URLs and drop duplicates by normalized URL or content fingerprint.
      - Remove low-reliability web sources.
      - Cap overrepresented domains to improve source diversity.
      - Prefer high-reliability, content-rich, first-party sources.
      - Add a lightweight curated excerpt to help downstream analysis.
    """
    canonical_sources: list[tuple[int, dict[str, Any]]] = []
    annotated_sources: list[dict[str, Any] | None] = [None] * len(sources)
    seen_url_keys: set[str] = set()
    seen_content_keys: set[str] = set()
    domain_counts: defaultdict[str, int] = defaultdict(int)
    kept: list[dict[str, Any]] = []
    removed_reasons: defaultdict[str, int] = defaultdict(int)

    for index, source in enumerate(sources):
        normalized_url = _normalize_url(source.get("url"))
        content_key = _content_fingerprint(source)
        if normalized_url and normalized_url in seen_url_keys:
            removed_reasons["duplicate_url"] += 1
            annotated_sources[index] = _annotate_source(
                source,
                included=False,
                reason="duplicate_url",
            )
            continue
        if content_key and content_key in seen_content_keys:
            removed_reasons["duplicate_content"] += 1
            annotated_sources[index] = _annotate_source(
                source,
                included=False,
                reason="duplicate_content",
            )
            continue
        canonical_sources.append((index, source))
        if normalized_url:
            seen_url_keys.add(normalized_url)
        if content_key:
            seen_content_keys.add(content_key)

    seen_url_keys.clear()
    seen_content_keys.clear()

    ranked_sources = sorted(
        canonical_sources,
        key=lambda item: (
            _is_first_party(item[1]),
            float(item[1].get("reliability_score", 0.0)),
            len((item[1].get("content_snippet") or "").strip()),
            -item[0],
        ),
        reverse=True,
    )

    for ranked_index, (source_index, source) in enumerate(ranked_sources):
        source_type = str(source.get("type", "url"))
        reliability = float(source.get("reliability_score", 0.0))
        if source_type not in FIRST_PARTY_SOURCE_TYPES and reliability < min_reliability_score:
            removed_reasons["low_reliability"] += 1
            annotated_sources[source_index] = _annotate_source(
                source,
                included=False,
                reason="low_reliability",
            )
            continue

        domain_key = _domain_key(source)
        if domain_key and not _is_first_party(source):
            if domain_counts[domain_key] >= max_sources_per_domain:
                removed_reasons["domain_cap"] += 1
                annotated_sources[source_index] = _annotate_source(
                    source,
                    included=False,
                    reason="domain_cap",
                    domain_key=domain_key,
                )
                continue

        curated = _annotate_source(
            source,
            included=True,
            reason="selected",
            domain_key=domain_key,
        )
        kept.append(curated)
        annotated_sources[source_index] = curated
        if domain_key:
            domain_counts[domain_key] += 1

        if len(kept) >= max_sources:
            for remaining_source_index, remaining_source in ranked_sources[ranked_index + 1:]:
                removed_reasons["max_source_cap"] += 1
                annotated_sources[remaining_source_index] = _annotate_source(
                    remaining_source,
                    included=False,
                    reason="max_source_cap",
                )
            break

    finalized_sources = [source for source in annotated_sources if source is not None]

    summary = {
        "input_count": len(sources),
        "kept_count": len(kept),
        "removed_count": len(sources) - len(kept),
        "first_party_count": sum(1 for item in kept if _is_first_party(item)),
        "avg_reliability": round(
            sum(float(item.get("reliability_score", 0.0)) for item in kept) / len(kept),
            4,
        ) if kept else 0.0,
        "removed_reasons": dict(removed_reasons),
    }
    return CuratedSourcesResult(
        sources=kept,
        all_sources=finalized_sources,
        removed_count=len(sources) - len(kept),
        summary=summary,
    )


def merge_source_sets(
    existing_sources: list[dict[str, Any]],
    incoming_sources: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Merge sources while preserving existing items and skipping obvious duplicates."""
    merged: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_url_keys: set[str] = set()
    seen_content_keys: set[str] = set()

    for source in [*existing_sources, *incoming_sources]:
        source_id = str(source.get("id", "")).strip()
        normalized_url = _normalize_url(source.get("url"))
        content_key = _content_fingerprint(source)

        if source_id and source_id in seen_ids:
            continue
        if normalized_url and normalized_url in seen_url_keys:
            continue
        if content_key and content_key in seen_content_keys:
            continue

        merged.append(dict(source))
        if source_id:
            seen_ids.add(source_id)
        if normalized_url:
            seen_url_keys.add(normalized_url)
        if content_key:
            seen_content_keys.add(content_key)

    return merged


def _is_first_party(source: dict[str, Any]) -> bool:
    return str(source.get("type", "")).lower() in FIRST_PARTY_SOURCE_TYPES


def _normalize_url(url: str | None) -> str:
    if not url:
        return ""
    try:
        parsed = urlparse(url.strip())
    except Exception:
        return ""
    if not parsed.scheme or not parsed.netloc:
        return ""
    normalized_path = parsed.path.rstrip("/")
    return f"{parsed.scheme}://{parsed.netloc}{normalized_path}".lower()


def _domain_key(source: dict[str, Any]) -> str:
    url = source.get("url")
    if not url:
        return f"type:{source.get('type', 'unknown')}"
    try:
        return (urlparse(str(url)).hostname or "").lower()
    except Exception:
        return ""


def _content_fingerprint(source: dict[str, Any]) -> str:
    title = re.sub(r"\s+", " ", str(source.get("title", "")).strip().lower())
    snippet = re.sub(r"\s+", " ", str(source.get("content_snippet", "")).strip().lower())
    if not title and not snippet:
        return ""
    return f"{title}|{snippet[:160]}"


def _build_curated_excerpt(source: dict[str, Any]) -> str:
    title = str(source.get("title", "")).strip()
    snippet = re.sub(r"\s+", " ", str(source.get("content_snippet", "")).strip())
    excerpt = snippet[:MAX_SNIPPET_LENGTH]
    if title and excerpt and title.lower() not in excerpt.lower():
        return f"{title}: {excerpt}"
    return excerpt or title


def _build_curation_tags(source: dict[str, Any], domain_key: str) -> list[str]:
    tags: list[str] = []
    if _is_first_party(source):
        tags.append("first_party")
    reliability = float(source.get("reliability_score", 0.0))
    if reliability >= 0.85:
        tags.append("high_confidence")
    elif reliability >= 0.7:
        tags.append("medium_confidence")
    else:
        tags.append("low_confidence")
    if domain_key:
        tags.append(f"domain:{domain_key}")
    return tags


def _annotate_source(
    source: dict[str, Any],
    *,
    included: bool,
    reason: str,
    domain_key: str | None = None,
) -> dict[str, Any]:
    resolved_domain_key = domain_key if domain_key is not None else _domain_key(source)
    annotated = dict(source)
    annotated["included_in_analysis"] = included
    annotated["curation_reason"] = reason
    annotated["curated_excerpt"] = _build_curated_excerpt(source)
    annotated["curation_tags"] = _build_curation_tags(source, resolved_domain_key)
    return annotated
