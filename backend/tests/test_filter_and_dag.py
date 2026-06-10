"""Tests for filter_node and qa_router logic."""

import pytest

from app.agents.fieldwork import FieldworkAgent
from app.orchestration import graph as graph_module
from app.orchestration.graph import (
    MAX_RETRIES,
    curate_node,
    filter_node,
    qa_node,
    qa_router,
    screenshot_node,
)


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


class TestCurateNode:
    @pytest.mark.asyncio
    async def test_curate_node_filters_duplicate_and_low_quality_sources(self):
        state = {
            "task_id": "t-curate",
            "sources": [
                {
                    "id": "s1",
                    "type": "url",
                    "url": "https://example.com/pricing",
                    "title": "Pricing",
                    "content_snippet": "Official pricing page",
                    "reliability_score": 0.9,
                },
                {
                    "id": "s2",
                    "type": "url",
                    "url": "https://example.com/pricing?source=dup",
                    "title": "Pricing dup",
                    "content_snippet": "Official pricing page",
                    "reliability_score": 0.91,
                },
                {
                    "id": "s3",
                    "type": "url",
                    "url": "https://blog.example.net/post",
                    "title": "Weak post",
                    "content_snippet": "opinion only",
                    "reliability_score": 0.4,
                },
                {
                    "id": "s4",
                    "type": "survey",
                    "title": "[模拟] Survey",
                    "content_snippet": "Primary signal",
                    "reliability_score": 0.55,
                },
            ],
            "traces": [],
        }

        result = await curate_node(state)
        curated_ids = {item["id"] for item in result["curated_sources"]}
        assert curated_ids == {"s1", "s4"}
        assert result["curation_summary"]["removed_count"] == 2
        assert result["status"] == "analyzing"
        assert result["traces"][-1]["agent_name"] == "curator"

    def test_routes_to_write_when_unknown_target(self):
        state = {
            "qa_feedback": {"passed": False, "retry_target": "unknown"},
            "retry_count": 0,
        }
        assert qa_router(state) == "write"


class TestCuratedSourceDownstreamUsage:
    @pytest.mark.asyncio
    async def test_screenshot_node_prefers_curated_sources(self, monkeypatch):
        captured: dict[str, list[str]] = {}

        async def fake_screenshot_webpages(urls, task_id):
            captured["urls"] = list(urls)
            captured["task_id"] = [task_id]
            return [{"url": url, "path": f"/tmp/{index}.png"} for index, url in enumerate(urls, 1)]

        monkeypatch.setattr(graph_module, "screenshot_webpages", fake_screenshot_webpages)

        state = {
            "task_id": "t-shot",
            "task": {
                "competitors": [
                    {"name": "Comp A", "website": "https://comp-a.example.com"},
                ],
            },
            "sources": [
                {"id": "raw-1", "url": "https://raw.example.com"},
            ],
            "curated_sources": [
                {"id": "cur-1", "url": "https://curated.example.com"},
            ],
            "traces": [],
        }

        result = await screenshot_node(state)

        assert captured["urls"] == [
            "https://comp-a.example.com",
            "https://curated.example.com",
        ]
        assert result["status"] == "filtering"
        assert len(result["screenshot_paths"]) == 2

    @pytest.mark.asyncio
    async def test_qa_node_prefers_curated_sources(self, monkeypatch):
        captured: dict[str, list[dict]] = {}

        def fake_validate_report_completeness(report, sources, **kwargs):
            captured["validated_sources"] = list(sources)
            return []

        def fake_enforce_competitive_schema(analysis, competitors):
            return []

        async def fake_qa_run(input_data):
            captured["qa_sources"] = list(input_data["sources"])
            return {
                "qa_feedback": {
                    "passed": True,
                    "issues": [],
                    "retry_target": "",
                    "constraints": [],
                },
                "metrics": {
                    "source_count": len(input_data["sources"]),
                    "claim_count": 1,
                    "evidence_coverage_rate": 1.0,
                },
                "handoff": {},
                "traces": [],
                "_llm_response": {"input_tokens": 1, "output_tokens": 1, "duration": 0.1},
            }

        monkeypatch.setattr(graph_module, "validate_report_completeness", fake_validate_report_completeness)
        monkeypatch.setattr(graph_module, "enforce_competitive_schema", fake_enforce_competitive_schema)
        monkeypatch.setattr(graph_module._qa, "run", fake_qa_run)

        curated_sources = [{"id": "cur-1", "title": "Curated"}]
        raw_sources = [{"id": "raw-1", "title": "Raw"}]
        state = {
            "task_id": "t-qa",
            "task": {"competitors": []},
            "report": {"title": "Report", "executive_summary": "x" * 60, "sections": []},
            "analysis": {},
            "sources": raw_sources,
            "curated_sources": curated_sources,
            "traces": [],
            "retry_count": 0,
        }

        result = await qa_node(state)

        assert captured["validated_sources"] == curated_sources
        assert captured["qa_sources"] == curated_sources
        assert result["metrics"]["source_count"] == 1
        assert result["status"] == "completed"


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
        assert result["status"] == "curating"
