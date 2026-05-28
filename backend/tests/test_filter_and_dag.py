"""Tests for filter_node and qa_router logic."""

import pytest

from app.orchestration.graph import filter_node, qa_router, MAX_RETRIES


class TestFilterNode:
    @pytest.mark.asyncio
    async def test_removes_claims_without_evidence(self):
        state = {
            "task_id": "t1",
            "report": {
                "title": "Test Report",
                "sections": [
                    {
                        "title": "Features",
                        "claims": [
                            {"content": "claim1", "evidence_ids": ["e1"]},
                            {"content": "claim2", "evidence_ids": []},
                            {"content": "claim3"},
                        ],
                    },
                ],
            },
            "traces": [],
        }
        result = await filter_node(state)
        sections = result["report"]["sections"]
        assert len(sections) == 1
        assert len(sections[0]["claims"]) == 1
        assert sections[0]["claims"][0]["content"] == "claim1"

    @pytest.mark.asyncio
    async def test_preserves_all_when_all_have_evidence(self):
        state = {
            "task_id": "t2",
            "report": {
                "title": "Test",
                "sections": [
                    {
                        "title": "S1",
                        "claims": [
                            {"content": "c1", "evidence_ids": ["e1"]},
                            {"content": "c2", "evidence_ids": ["e2", "e3"]},
                        ],
                    },
                ],
            },
            "traces": [],
        }
        result = await filter_node(state)
        assert len(result["report"]["sections"][0]["claims"]) == 2

    @pytest.mark.asyncio
    async def test_empty_sections(self):
        state = {"task_id": "t3", "report": {"sections": []}, "traces": []}
        result = await filter_node(state)
        assert result["report"]["sections"] == []


class TestQaRouter:
    def test_passed_returns_end(self):
        state = {"qa_feedback": {"passed": True}, "retry_count": 0}
        assert qa_router(state) == "__end__"

    def test_retries_exceeded_returns_end(self):
        state = {
            "qa_feedback": {"passed": False, "retry_target": "collector"},
            "retry_count": MAX_RETRIES + 1,
        }
        assert qa_router(state) == "__end__"

    def test_routes_to_collect(self):
        state = {
            "qa_feedback": {"passed": False, "retry_target": "collector"},
            "retry_count": 1,
        }
        assert qa_router(state) == "collect"

    def test_routes_to_analyze(self):
        state = {
            "qa_feedback": {"passed": False, "retry_target": "analyst"},
            "retry_count": 1,
        }
        assert qa_router(state) == "analyze"

    def test_routes_to_write_default(self):
        state = {
            "qa_feedback": {"passed": False, "retry_target": "writer"},
            "retry_count": 1,
        }
        assert qa_router(state) == "write"

    def test_routes_to_write_when_unknown_target(self):
        state = {
            "qa_feedback": {"passed": False, "retry_target": "unknown"},
            "retry_count": 0,
        }
        assert qa_router(state) == "write"
