"""Tests for filter_node and qa_router logic."""

import pytest

from app.agents.fieldwork import FieldworkAgent
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


class TestFieldworkSources:
    """Fieldwork must fold simulated survey/interview results back into the
    evidence pool as citable SURVEY/INTERVIEW sources (the closed loop)."""

    def test_build_sources_from_survey_and_interview(self):
        fieldwork = {
            "survey_results": [
                {
                    "persona": "Team Buyers",
                    "respondent_count": 150,
                    "answers": [
                        {"question_id": "q1", "dimension": "pricing", "answer": "60% want cheaper tier"},
                    ],
                    "key_findings": ["Price sensitivity is high"],
                },
            ],
            "interview_transcripts": [
                {
                    "persona": "Power Users",
                    "excerpts": [
                        {"question_id": "iq1", "dimension": "switching", "quote": "Lock-in keeps us.", "insight": "Switching cost moat"},
                    ],
                    "key_findings": ["Databases create lock-in"],
                },
            ],
            "summary": "synthetic",
        }
        sources = FieldworkAgent._build_sources(fieldwork)
        assert len(sources) == 2

        survey_src = next(s for s in sources if s["type"] == "survey")
        interview_src = next(s for s in sources if s["type"] == "interview")

        # Flagged as simulated, carry an ID for citation linking, scored as primary research
        assert survey_src["title"].startswith("[模拟]")
        assert interview_src["title"].startswith("[模拟]")
        assert survey_src["id"] and interview_src["id"]
        assert "Price sensitivity" in survey_src["content_snippet"]
        assert "Lock-in keeps us" in interview_src["content_snippet"]
        assert 0 < survey_src["reliability_score"] <= 0.6

    def test_build_sources_empty(self):
        assert FieldworkAgent._build_sources({}) == []

    @pytest.mark.asyncio
    async def test_fieldwork_node_merges_sources_into_state(self, monkeypatch):
        """fieldwork_node must append its sources to existing state sources."""
        from app.orchestration import graph

        async def fake_run(_input):
            return {
                "fieldwork": {"summary": "ok"},
                "sources": [{"id": "fw1", "type": "survey", "title": "[模拟] S", "content_snippet": "x", "reliability_score": 0.55}],
                "traces": [],
                "_llm_response": {"input_tokens": 1, "output_tokens": 1, "duration": 0.1},
            }

        monkeypatch.setattr(graph._fieldwork, "run", fake_run)
        state = {
            "task_id": "t1",
            "task": {"target_product": "P", "competitors": ["A"]},
            "sources": [{"id": "web1", "type": "url", "title": "Web"}],
            "survey": {"questions": []},
            "interview": {"questions": []},
            "analysis": {},
            "traces": [],
        }
        result = await graph.fieldwork_node(state)
        ids = {s["id"] for s in result["sources"]}
        assert ids == {"web1", "fw1"}
        assert result["status"] == "analyzing"
