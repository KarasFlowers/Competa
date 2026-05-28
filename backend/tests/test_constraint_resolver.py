"""Tests for the ratchet constraint resolver."""

from app.orchestration.constraint_resolver import (
    build_handoff,
    determine_retry_target,
    issues_to_constraints,
)


class TestDetermineRetryTarget:
    def test_missing_field_goes_to_collector(self):
        issues = [{"issue_type": "missing_field", "field_path": "sources", "description": ""}]
        assert determine_retry_target(issues) == "collector"

    def test_missing_evidence_goes_to_analyst(self):
        issues = [{"issue_type": "missing_evidence", "field_path": "", "description": ""}]
        assert determine_retry_target(issues) == "analyst"

    def test_low_coverage_goes_to_collector(self):
        issues = [{"issue_type": "low_coverage", "description": "need more sources"}]
        assert determine_retry_target(issues) == "collector"

    def test_schema_violation_goes_to_analyst(self):
        issues = [{"issue_type": "schema_violation", "field_path": "pricing", "description": ""}]
        assert determine_retry_target(issues) == "analyst"

    def test_mixed_issues_pick_earliest_stage(self):
        issues = [
            {"issue_type": "missing_evidence", "description": ""},
            {"issue_type": "low_coverage", "description": ""},
        ]
        # collector < analyst, so collector wins
        assert determine_retry_target(issues) == "collector"

    def test_empty_issues_defaults_to_writer(self):
        assert determine_retry_target([]) == "writer"


class TestIssuesToConstraints:
    def test_missing_field_constraint(self):
        issues = [{"issue_type": "missing_field", "field_path": "pricing_models", "description": ""}]
        constraints = issues_to_constraints(issues)
        assert len(constraints) == 1
        assert "pricing_models" in constraints[0]
        assert "CONSTRAINT" in constraints[0]

    def test_missing_evidence_constraint(self):
        issues = [{"issue_type": "missing_evidence", "description": "claims lack sources"}]
        constraints = issues_to_constraints(issues)
        assert len(constraints) == 1
        assert "evidence_id" in constraints[0]

    def test_low_coverage_constraint(self):
        issues = [{"issue_type": "low_coverage", "description": "only 2 sources found"}]
        constraints = issues_to_constraints(issues)
        assert len(constraints) == 1
        assert "coverage" in constraints[0].lower()

    def test_generic_description_fallback(self):
        issues = [{"issue_type": "unknown", "description": "something went wrong"}]
        constraints = issues_to_constraints(issues)
        assert len(constraints) == 1
        assert "something went wrong" in constraints[0]

    def test_empty_issues(self):
        assert issues_to_constraints([]) == []


class TestBuildHandoff:
    def test_basic_handoff(self):
        issues = [
            {"issue_type": "missing_field", "field_path": "personas", "description": "empty personas"},
        ]
        handoff = build_handoff(issues, current_retry_count=0, max_retries=2)
        assert handoff.target_agent == "collector"
        assert handoff.issue_type == "missing_field"
        assert "personas" in handoff.failed_fields
        assert handoff.max_retries == 2
        assert len(handoff.constraints) >= 1

    def test_handoff_decrements_retries(self):
        issues = [{"issue_type": "missing_evidence", "description": "no evidence"}]
        handoff = build_handoff(issues, current_retry_count=1, max_retries=2)
        assert handoff.max_retries == 1

    def test_handoff_evidence_requirements(self):
        issues = [
            {"issue_type": "missing_evidence", "description": "claims A and B lack sources"},
        ]
        handoff = build_handoff(issues, current_retry_count=0)
        assert "claims A and B lack sources" in handoff.evidence_requirements
