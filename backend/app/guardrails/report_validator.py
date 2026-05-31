"""Deterministic report completeness checks — runs before LLM-based QA.

These checks complement the LLM QA agent with code-verified rules that
the LLM might miss or be too lenient on.  Any failure produces a
structured issue dict compatible with the existing QA issue format.
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Configuration — minimum thresholds for a "complete" report
# ---------------------------------------------------------------------------

MIN_TOTAL_CLAIMS = 6
MIN_SECTIONS = 4
MIN_EVIDENCE_COVERAGE = 0.8  # 80% of claims must have evidence
MIN_EXECUTIVE_SUMMARY_CHARS = 50
REQUIRED_SECTION_KEYWORDS: list[str] = []  # optional: e.g. ["feature", "pricing", "swot"]


# ---------------------------------------------------------------------------
# Core validation
# ---------------------------------------------------------------------------

def validate_report_completeness(
    report: dict[str, Any],
    sources: list[dict[str, Any]],
    *,
    min_claims: int = MIN_TOTAL_CLAIMS,
    min_sections: int = MIN_SECTIONS,
    min_evidence_coverage: float = MIN_EVIDENCE_COVERAGE,
    min_summary_chars: int = MIN_EXECUTIVE_SUMMARY_CHARS,
    required_keywords: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Run deterministic checks on the report and return a list of issues.

    Each issue dict matches the QA issue schema:
        {issue_type, field_path, description, severity}
    """
    issues: list[dict[str, Any]] = []

    # --- 1. Executive summary must exist and be non-trivial ---
    summary = report.get("executive_summary", "")
    if not summary or len(summary.strip()) < min_summary_chars:
        issues.append({
            "issue_type": "missing_field",
            "field_path": "executive_summary",
            "description": (
                f"Executive summary is missing or too short "
                f"({len(summary.strip())} chars, minimum {min_summary_chars})."
            ),
            "severity": "critical",
        })

    # --- 2. Minimum number of top-level sections ---
    sections: list[dict] = report.get("sections", [])
    if len(sections) < min_sections:
        issues.append({
            "issue_type": "missing_field",
            "field_path": "sections",
            "description": (
                f"Report has {len(sections)} top-level section(s), "
                f"minimum required is {min_sections}."
            ),
            "severity": "critical",
        })

    # --- 3. Required section keywords (soft match on title) ---
    keywords = required_keywords or REQUIRED_SECTION_KEYWORDS
    if keywords:
        section_titles_lower = [s.get("title", "").lower() for s in sections]
        for kw in keywords:
            if not any(kw in t for t in section_titles_lower):
                issues.append({
                    "issue_type": "missing_field",
                    "field_path": f"sections[?title~{kw}]",
                    "description": (
                        f"No section found matching keyword '{kw}'."
                    ),
                    "severity": "warning",
                })

    # --- 4. Count claims and evidence coverage recursively ---
    total_claims, claims_with_evidence = _count_claims(sections)
    if total_claims < min_claims:
        issues.append({
            "issue_type": "low_coverage",
            "field_path": "sections.claims",
            "description": (
                f"Report contains {total_claims} claim(s), "
                f"minimum required is {min_claims}."
            ),
            "severity": "critical",
        })

    if total_claims > 0:
        coverage = claims_with_evidence / total_claims
        if coverage < min_evidence_coverage:
            issues.append({
                "issue_type": "missing_evidence",
                "field_path": "sections.claims.evidence_ids",
                "description": (
                    f"Evidence coverage is {coverage:.0%} "
                    f"({claims_with_evidence}/{total_claims}), "
                    f"minimum required is {min_evidence_coverage:.0%}."
                ),
                "severity": "critical",
            })

    # --- 5. Source count check ---
    if len(sources) < 3:
        issues.append({
            "issue_type": "low_coverage",
            "field_path": "sources",
            "description": (
                f"Only {len(sources)} source(s) available; "
                f"at least 3 are expected for a credible report."
            ),
            "severity": "warning",
        })

    return issues


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _count_claims(sections: list[dict]) -> tuple[int, int]:
    """Recursively count total claims and claims with evidence.

    Returns (total_claims, claims_with_evidence).
    """
    total = 0
    with_evidence = 0
    for section in sections:
        for claim in section.get("claims", []):
            total += 1
            if claim.get("evidence_ids"):
                with_evidence += 1
        sub_total, sub_with = _count_claims(section.get("subsections", []))
        total += sub_total
        with_evidence += sub_with
    return total, with_evidence
