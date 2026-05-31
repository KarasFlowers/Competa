"""Tests for the Guardrails validation layer."""

import pytest

from app.guardrails.report_validator import validate_report_completeness
from app.guardrails.validator import GuardrailError, validate_output
from app.schemas.base import Source, SourceType
from app.schemas.competitive import PricingModel, PricingModelType
from app.schemas.ratchet import TaskMetrics


class TestValidateOutput:
    def test_valid_dict(self):
        data = {"type": "url", "title": "Example", "url": "https://example.com"}
        result = validate_output(Source, data)
        assert isinstance(result, Source)
        assert result.title == "Example"

    def test_valid_json_string(self):
        json_str = '{"type": "document", "title": "Doc"}'
        result = validate_output(Source, json_str)
        assert result.type == SourceType.DOCUMENT

    def test_valid_instance_passthrough(self):
        s = Source(type=SourceType.URL, title="T")
        result = validate_output(Source, s)
        assert result is s

    def test_invalid_raises_guardrail_error(self):
        with pytest.raises(GuardrailError) as exc_info:
            validate_output(Source, {"type": "invalid_type"})
        err = exc_info.value
        assert len(err.errors) > 0
        assert err.schema_name == "Source"

    def test_missing_required_field(self):
        with pytest.raises(GuardrailError) as exc_info:
            validate_output(PricingModel, {"tiers": []})
        err = exc_info.value
        error_dict = err.to_dict()
        assert error_dict["error_count"] > 0
        field_paths = [e["field_path"] for e in error_dict["errors"]]
        assert any("product_name" in fp for fp in field_paths)

    def test_value_out_of_range(self):
        with pytest.raises(GuardrailError):
            validate_output(
                TaskMetrics,
                {"task_id": "t1", "evidence_coverage_rate": 2.0},
            )

    def test_error_has_suggestions(self):
        with pytest.raises(GuardrailError) as exc_info:
            validate_output(Source, {})
        err = exc_info.value
        for fe in err.errors:
            assert isinstance(fe.suggestion, str)


# ---------------------------------------------------------------------------
# Report completeness hard validator
# ---------------------------------------------------------------------------

def _make_report(
    summary="A" * 60,
    sections=None,
    claims_per_section=3,
    with_evidence=True,
) -> dict:
    """Build a minimal valid report dict for testing."""
    if sections is None:
        sections = []
        for i in range(4):
            claims = []
            for j in range(claims_per_section):
                claim = {
                    "id": f"claim_{i}_{j}",
                    "content": f"Claim {i}-{j}",
                    "evidence_ids": [f"src_{i}_{j}"] if with_evidence else [],
                }
                claims.append(claim)
            sections.append({"title": f"Section {i}", "content": "...", "claims": claims})
    return {"title": "Test Report", "executive_summary": summary, "sections": sections}


def _make_sources(count=5) -> list[dict]:
    return [{"id": f"src_{i}", "type": "url", "url": f"https://example.com/{i}"} for i in range(count)]


class TestReportCompletenessValidator:
    def test_valid_report_no_issues(self):
        report = _make_report()
        sources = _make_sources()
        issues = validate_report_completeness(report, sources)
        assert issues == []

    def test_missing_executive_summary(self):
        report = _make_report(summary="")
        issues = validate_report_completeness(report, _make_sources())
        assert any(i["field_path"] == "executive_summary" for i in issues)
        assert any(i["severity"] == "critical" for i in issues)

    def test_too_short_summary(self):
        report = _make_report(summary="short")
        issues = validate_report_completeness(report, _make_sources())
        assert any(i["field_path"] == "executive_summary" for i in issues)

    def test_too_few_sections(self):
        report = _make_report(sections=[{"title": "Only one", "claims": []}])
        issues = validate_report_completeness(report, _make_sources())
        assert any(i["field_path"] == "sections" for i in issues)

    def test_too_few_claims(self):
        report = _make_report(claims_per_section=1)
        issues = validate_report_completeness(report, _make_sources())
        assert any(i["issue_type"] == "low_coverage" and "claim" in i["field_path"] for i in issues)

    def test_low_evidence_coverage(self):
        report = _make_report(with_evidence=False)
        issues = validate_report_completeness(report, _make_sources())
        assert any(i["issue_type"] == "missing_evidence" for i in issues)

    def test_too_few_sources(self):
        report = _make_report()
        issues = validate_report_completeness(report, [])
        assert any(i["field_path"] == "sources" for i in issues)

    def test_required_keywords_missing(self):
        report = _make_report()
        issues = validate_report_completeness(
            report, _make_sources(), required_keywords=["pricing", "swot"]
        )
        assert any("pricing" in i["description"] for i in issues)
        assert any("swot" in i["description"] for i in issues)

    def test_required_keywords_present(self):
        sections = [
            {"title": "Feature Comparison", "claims": [{"id": "c1", "content": "x", "evidence_ids": ["s1"]}] * 3},
            {"title": "Pricing Analysis", "claims": [{"id": "c2", "content": "y", "evidence_ids": ["s2"]}] * 3},
            {"title": "SWOT Analysis", "claims": [{"id": "c3", "content": "z", "evidence_ids": ["s3"]}] * 3},
            {"title": "Conclusions", "claims": [{"id": "c4", "content": "w", "evidence_ids": ["s4"]}] * 3},
        ]
        report = _make_report(sections=sections)
        issues = validate_report_completeness(
            report, _make_sources(), required_keywords=["pricing", "swot"]
        )
        keyword_issues = [i for i in issues if "keyword" in i.get("description", "")]
        assert len(keyword_issues) == 0
