"""Tests for the Guardrails validation layer."""

import pytest

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
