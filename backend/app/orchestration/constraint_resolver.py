"""Ratchet constraint resolver — converts QA issues to reusable constraint rules."""

from __future__ import annotations

from typing import Any

from app.schemas.handoff import HandoffInstruction

# Priority order: issues targeting earlier pipeline stages take precedence.
_STAGE_PRIORITY = {"collector": 0, "analyst": 1, "writer": 2}

# Mapping from issue_type to target agent
_ISSUE_TARGET_MAP = {
    "missing_field": "collector",
    "low_coverage": "collector",
    "missing_evidence": "analyst",
    "schema_violation": "analyst",
}


def determine_retry_target(issues: list[dict[str, Any]]) -> str:
    """Pick the Agent to retry based on issue types. Prefer earliest stage."""
    targets: set[str] = set()
    for issue in issues:
        t = _ISSUE_TARGET_MAP.get(issue.get("issue_type", ""), "writer")
        targets.add(t)
    if not targets:
        return "writer"
    return min(targets, key=lambda t: _STAGE_PRIORITY.get(t, 99))


def issues_to_constraints(issues: list[dict[str, Any]]) -> list[str]:
    """Convert QA issues into human-readable constraint strings for prompt injection."""
    constraints: list[str] = []
    for issue in issues:
        itype = issue.get("issue_type", "")
        desc = issue.get("description", "")
        field = issue.get("field_path", "")

        if itype == "missing_field" and field:
            constraints.append(f"CONSTRAINT: field '{field}' must not be empty.")
        elif itype == "missing_evidence":
            constraints.append(
                f"CONSTRAINT: every claim must have at least one evidence_id. {desc}"
            )
        elif itype == "low_coverage":
            constraints.append(
                f"CONSTRAINT: increase source coverage. {desc}"
            )
        elif itype == "schema_violation" and field:
            constraints.append(
                f"CONSTRAINT: fix schema violation at '{field}'. {desc}"
            )
        elif desc:
            constraints.append(f"CONSTRAINT: {desc}")
    return constraints


def build_handoff(
    issues: list[dict[str, Any]],
    current_retry_count: int,
    max_retries: int = 2,
) -> HandoffInstruction:
    """Build a structured handoff instruction from QA issues."""
    target = determine_retry_target(issues)
    constraints = issues_to_constraints(issues)
    failed_fields = [
        issue["field_path"]
        for issue in issues
        if issue.get("field_path")
    ]
    # Pick the dominant issue type
    issue_types = [issue.get("issue_type", "") for issue in issues]
    dominant_type = max(set(issue_types), key=issue_types.count) if issue_types else "unknown"

    evidence_reqs = "; ".join(
        issue.get("description", "")
        for issue in issues
        if issue.get("issue_type") == "missing_evidence"
    )

    return HandoffInstruction(
        target_agent=target,
        issue_type=dominant_type,
        failed_fields=failed_fields,
        evidence_requirements=evidence_reqs,
        max_retries=max_retries - current_retry_count,
        constraints=constraints,
    )
