"""Tests for LLM Adapter — MockLLM output compliance."""

import pytest
from app.llm.adapter import MockLLM
from app.schemas.base import CollectResult, AnalyzeResult, WriteResult, QAFeedback


@pytest.fixture
def mock_llm():
    return MockLLM()


class TestMockLLM:
    async def test_collect_result(self, mock_llm):
        result = await mock_llm.generate(
            "collect", CollectResult,
            competitors=["A", "B"], target_product="Target",
        )
        assert isinstance(result, CollectResult)
        assert len(result.sources) > 0
        for s in result.sources:
            assert s.title
            assert s.url

    async def test_analyze_result(self, mock_llm):
        result = await mock_llm.generate(
            "analyze", AnalyzeResult,
            competitors=["A", "B"],
        )
        assert isinstance(result, AnalyzeResult)
        assert len(result.feature_trees) == 2
        assert len(result.pricing_models) == 2
        assert len(result.personas) == 2
        assert len(result.swot_analyses) == 2

    async def test_write_result(self, mock_llm):
        result = await mock_llm.generate(
            "write", WriteResult,
            competitors=["A"], target_product="Target", sources=[],
        )
        assert isinstance(result, WriteResult)
        assert isinstance(result.report, dict)
        assert "title" in result.report

    async def test_qa_first_call_fails(self, mock_llm):
        result = await mock_llm.generate("qa", QAFeedback)
        assert isinstance(result, QAFeedback)
        assert result.passed is False
        assert len(result.issues) > 0
        assert result.retry_target == "write"
        assert len(result.constraints) > 0

    async def test_qa_second_call_passes(self, mock_llm):
        await mock_llm.generate("qa", QAFeedback)  # first call fails
        result = await mock_llm.generate("qa", QAFeedback)  # second call passes
        assert isinstance(result, QAFeedback)
        assert result.passed is True
        assert len(result.issues) == 0

    async def test_unsupported_schema_raises(self, mock_llm):
        from pydantic import BaseModel

        class Unsupported(BaseModel):
            x: int = 1

        with pytest.raises(ValueError, match="does not support"):
            await mock_llm.generate("test", Unsupported)
