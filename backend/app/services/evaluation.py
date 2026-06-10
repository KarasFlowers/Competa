"""Deterministic quality evaluation for completed pipeline runs."""

from __future__ import annotations

from typing import Any


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _iter_sections(sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    collected: list[dict[str, Any]] = []
    for section in sections:
        if not isinstance(section, dict):
            continue
        collected.append(section)
        subsections = section.get("subsections", [])
        if isinstance(subsections, list):
            collected.extend(_iter_sections(subsections))
    return collected


def _collect_claims(report: dict[str, Any]) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    for section in _iter_sections(report.get("sections", []) or []):
        section_claims = section.get("claims", [])
        if isinstance(section_claims, list):
            claims.extend(claim for claim in section_claims if isinstance(claim, dict))
    return claims


def _score_schema_completeness(analysis: dict[str, Any], report: dict[str, Any]) -> float:
    checks = [
        bool(analysis.get("feature_trees")),
        bool(analysis.get("pricing_models")),
        bool(analysis.get("personas")),
        bool(analysis.get("swot_analyses")),
        bool(report.get("title")),
        bool(report.get("executive_summary") or report.get("sections")),
    ]
    return sum(1 for check in checks if check) / len(checks)


def _score_citation_density(claims: list[dict[str, Any]]) -> float:
    if not claims:
        return 0.0
    total_refs = sum(len(claim.get("evidence_ids") or []) for claim in claims)
    return _clamp((total_refs / len(claims)) / 2)


def _score_source_quality(sources: list[dict[str, Any]]) -> float:
    if not sources:
        return 0.0
    scores = [
        float(source.get("reliability_score", 0.0) or 0.0)
        for source in sources
        if isinstance(source, dict)
    ]
    if not scores:
        return 0.0
    return _clamp(sum(scores) / len(scores))


def evaluate_run_quality(
    final_state: dict[str, Any],
    metrics_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compute a stable 0-1 run quality score from persisted pipeline artifacts."""
    metrics = metrics_data or final_state.get("metrics", {}) or {}
    report = final_state.get("report", {}) or {}
    analysis = final_state.get("analysis", {}) or {}
    claims = _collect_claims(report)
    sources = final_state.get("curated_sources") or final_state.get("sources", []) or []

    evidence_coverage = _clamp(float(metrics.get("evidence_coverage_rate", 0.0) or 0.0))
    schema_completeness = _score_schema_completeness(analysis, report)
    citation_density = _score_citation_density(claims)
    source_quality = _score_source_quality(sources)

    weights = {
        "evidence_coverage": 0.4,
        "schema_completeness": 0.25,
        "citation_density": 0.2,
        "source_quality": 0.15,
    }
    score = (
        evidence_coverage * weights["evidence_coverage"]
        + schema_completeness * weights["schema_completeness"]
        + citation_density * weights["citation_density"]
        + source_quality * weights["source_quality"]
    )

    return {
        "score": round(_clamp(score), 4),
        "components": {
            "evidence_coverage": round(evidence_coverage, 4),
            "schema_completeness": round(schema_completeness, 4),
            "citation_density": round(citation_density, 4),
            "source_quality": round(source_quality, 4),
        },
        "weights": weights,
        "inputs": {
            "claim_count": len(claims),
            "source_count": len(sources),
        },
    }
