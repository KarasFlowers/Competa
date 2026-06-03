"""Competitive knowledge schema enforcement — validates that analysis output
conforms to the required competitive intelligence structure.

These checks complement Pydantic structural validation (which only enforces
field types) with business-level completeness rules.  Missing an entire
dimension (e.g. no feature trees) is a warning; empty data within a
present dimension (e.g. feature tree with no root nodes) is critical.

Returns a list of issue dicts compatible with the QA issue schema:
    {issue_type, field_path, description, severity}
"""

from __future__ import annotations

from typing import Any


# Required SWOT categories
_REQUIRED_SWOT_CATEGORIES = {"strength", "weakness", "opportunity", "threat"}


def enforce_competitive_schema(
    analysis: dict[str, Any],
    competitors: list[Any] | None = None,
) -> list[dict[str, Any]]:
    """Validate that analysis output satisfies competitive knowledge schema.

    Args:
        analysis: The analysis dict from AnalystAgent (AnalyzeResult.model_dump()).
        competitors: Optional list of competitor names/objects for cross-referencing.

    Returns:
        List of issue dicts with keys: issue_type, field_path, description, severity.
        severity is "warning" (non-blocking) or "critical" (blocking — triggers retry).
    """
    issues: list[dict[str, Any]] = []

    # --- 1. Feature trees ---
    feature_trees = analysis.get("feature_trees", [])
    if not feature_trees:
        issues.append({
            "issue_type": "missing_dimension",
            "field_path": "feature_trees",
            "description": "No feature comparison trees found — analysis lacks feature comparison.",
            "severity": "warning",
        })
    else:
        for i, tree in enumerate(feature_trees):
            product_name = tree.get("product_name", f"tree[{i}]")
            root_nodes = tree.get("root_nodes", [])
            if not root_nodes:
                issues.append({
                    "issue_type": "empty_dimension",
                    "field_path": f"feature_trees[{i}].root_nodes",
                    "description": (
                        f"Feature tree for '{product_name}' has no root nodes — "
                        f"feature comparison is empty."
                    ),
                    "severity": "critical",
                })

    # --- 2. Pricing models ---
    pricing_models = analysis.get("pricing_models", [])
    if not pricing_models:
        issues.append({
            "issue_type": "missing_dimension",
            "field_path": "pricing_models",
            "description": "No pricing models found — analysis lacks pricing comparison.",
            "severity": "warning",
        })
    else:
        for i, model in enumerate(pricing_models):
            product_name = model.get("product_name", f"pricing[{i}]")
            tiers = model.get("tiers", [])
            if not tiers:
                issues.append({
                    "issue_type": "empty_dimension",
                    "field_path": f"pricing_models[{i}].tiers",
                    "description": (
                        f"Pricing model for '{product_name}' has no tiers — "
                        f"pricing data is empty."
                    ),
                    "severity": "critical",
                })

    # --- 3. SWOT analyses ---
    swot_analyses = analysis.get("swot_analyses", [])
    if not swot_analyses:
        issues.append({
            "issue_type": "missing_dimension",
            "field_path": "swot_analyses",
            "description": "No SWOT analyses found — analysis lacks strategic assessment.",
            "severity": "warning",
        })
    else:
        for i, swot in enumerate(swot_analyses):
            product_name = swot.get("product_name", f"swot[{i}]")
            items = swot.get("items", [])
            if not items:
                issues.append({
                    "issue_type": "empty_dimension",
                    "field_path": f"swot_analyses[{i}].items",
                    "description": (
                        f"SWOT for '{product_name}' has no items — "
                        f"strategic assessment is empty."
                    ),
                    "severity": "critical",
                })
            else:
                # Check all four SWOT categories are present
                present_categories = {item.get("category", "") for item in items}
                missing = _REQUIRED_SWOT_CATEGORIES - present_categories
                if missing:
                    issues.append({
                        "issue_type": "incomplete_swot",
                        "field_path": f"swot_analyses[{i}].items",
                        "description": (
                            f"SWOT for '{product_name}' is missing categories: "
                            f"{', '.join(sorted(missing))}. "
                            f"A complete SWOT requires all four categories."
                        ),
                        "severity": "critical",
                    })

    # --- 4. Personas (warning only — not always required) ---
    personas = analysis.get("personas", [])
    if not personas:
        issues.append({
            "issue_type": "missing_dimension",
            "field_path": "personas",
            "description": "No user personas found — analysis lacks user segmentation.",
            "severity": "warning",
        })

    return issues
