"""Tests for the competitive knowledge schema enforcer."""

from app.guardrails.schema_enforcer import enforce_competitive_schema


def _complete_analysis() -> dict:
    """Return a fully-populated analysis dict that should pass all checks."""
    return {
        "feature_trees": [
            {
                "product_name": "ProductA",
                "root_nodes": [
                    {"name": "Core", "description": "Core features", "status": "supported", "children": []}
                ],
            }
        ],
        "pricing_models": [
            {
                "product_name": "ProductA",
                "tiers": [{"name": "Free", "price": "$0"}],
            }
        ],
        "swot_analyses": [
            {
                "product_name": "ProductA",
                "items": [
                    {"category": "strength", "content": "Strong brand"},
                    {"category": "weakness", "content": "High price"},
                    {"category": "opportunity", "content": "New market"},
                    {"category": "threat", "content": "New entrant"},
                ],
            }
        ],
        "personas": [
            {"name": "Enterprise User", "description": "Large org buyer"}
        ],
    }


class TestEnforceCompetitiveSchema:
    def test_complete_analysis_passes(self):
        issues = enforce_competitive_schema(_complete_analysis())
        assert issues == []

    def test_empty_feature_trees_warning(self):
        analysis = _complete_analysis()
        analysis["feature_trees"] = []
        issues = enforce_competitive_schema(analysis)
        assert len(issues) == 1
        assert issues[0]["field_path"] == "feature_trees"
        assert issues[0]["severity"] == "warning"
        assert issues[0]["issue_type"] == "missing_dimension"

    def test_feature_tree_empty_root_nodes_critical(self):
        analysis = _complete_analysis()
        analysis["feature_trees"] = [{"product_name": "X", "root_nodes": []}]
        issues = enforce_competitive_schema(analysis)
        assert len(issues) == 1
        assert issues[0]["severity"] == "critical"
        assert "root_nodes" in issues[0]["field_path"]

    def test_empty_pricing_models_warning(self):
        analysis = _complete_analysis()
        analysis["pricing_models"] = []
        issues = enforce_competitive_schema(analysis)
        assert len(issues) == 1
        assert issues[0]["field_path"] == "pricing_models"
        assert issues[0]["severity"] == "warning"

    def test_pricing_model_empty_tiers_critical(self):
        analysis = _complete_analysis()
        analysis["pricing_models"] = [{"product_name": "X", "tiers": []}]
        issues = enforce_competitive_schema(analysis)
        assert len(issues) == 1
        assert issues[0]["severity"] == "critical"
        assert "tiers" in issues[0]["field_path"]

    def test_empty_swot_warning(self):
        analysis = _complete_analysis()
        analysis["swot_analyses"] = []
        issues = enforce_competitive_schema(analysis)
        assert len(issues) == 1
        assert issues[0]["field_path"] == "swot_analyses"
        assert issues[0]["severity"] == "warning"

    def test_swot_empty_items_critical(self):
        analysis = _complete_analysis()
        analysis["swot_analyses"] = [{"product_name": "X", "items": []}]
        issues = enforce_competitive_schema(analysis)
        assert len(issues) == 1
        assert issues[0]["severity"] == "critical"
        assert "items" in issues[0]["field_path"]

    def test_swot_missing_categories_critical(self):
        analysis = _complete_analysis()
        # Remove 'threat' category
        analysis["swot_analyses"][0]["items"] = [
            {"category": "strength", "content": "S"},
            {"category": "weakness", "content": "W"},
            {"category": "opportunity", "content": "O"},
        ]
        issues = enforce_competitive_schema(analysis)
        assert len(issues) == 1
        assert issues[0]["severity"] == "critical"
        assert "threat" in issues[0]["description"]

    def test_empty_personas_warning(self):
        analysis = _complete_analysis()
        analysis["personas"] = []
        issues = enforce_competitive_schema(analysis)
        assert len(issues) == 1
        assert issues[0]["field_path"] == "personas"
        assert issues[0]["severity"] == "warning"

    def test_multiple_issues_accumulate(self):
        analysis = {"feature_trees": [], "pricing_models": [], "swot_analyses": [], "personas": []}
        issues = enforce_competitive_schema(analysis)
        assert len(issues) == 4
        severities = {i["severity"] for i in issues}
        assert severities == {"warning"}

    def test_missing_keys_treated_as_empty(self):
        """Analysis dict with missing keys should produce warnings."""
        issues = enforce_competitive_schema({})
        assert len(issues) == 4
        assert all(i["severity"] == "warning" for i in issues)

    def test_severity_critical_overrides_warning(self):
        """When a dimension is present but empty, it's critical not warning."""
        analysis = _complete_analysis()
        analysis["feature_trees"] = [{"product_name": "X", "root_nodes": []}]
        analysis["pricing_models"] = []
        issues = enforce_competitive_schema(analysis)
        assert len(issues) == 2
        field_paths = [i["field_path"] for i in issues]
        assert any("root_nodes" in fp for fp in field_paths)
        assert any(fp == "pricing_models" for fp in field_paths)
        # root_nodes empty is critical, pricing_models missing is warning
        for i in issues:
            if "root_nodes" in i["field_path"]:
                assert i["severity"] == "critical"
            if i["field_path"] == "pricing_models":
                assert i["severity"] == "warning"
