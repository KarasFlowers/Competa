"""Tests for all Pydantic schemas — serialisation round-trips and validation."""

import pytest
from app.schemas.base import (
    AgentMessage,
    AnalyzeRequest,
    AnalyzeResult,
    Claim,
    CollectRequest,
    CollectResult,
    Evidence,
    MessageType,
    QAFeedback,
    Source,
    SourceType,
    WriteRequest,
    WriteResult,
)
from app.schemas.competitive import (
    FeatureNode,
    FeatureStatus,
    FeatureTree,
    Persona,
    PricingModel,
    PricingModelType,
    PricingTier,
    SWOT,
    SWOTCategory,
    SWOTItem,
)
from app.schemas.report import Report, ReportSection
from app.schemas.agent import AgentRole, AgentRegistry, RoleType, default_registry
from app.schemas.ratchet import ConstraintRule, IssueType, QAIssue, Severity, TaskMetrics
from app.schemas.trace import AgentTrace, EventType, TraceEvent, TraceStatus


# ---------------------------------------------------------------------------
# base.py
# ---------------------------------------------------------------------------

class TestSource:
    def test_create_url_source(self):
        s = Source(type=SourceType.URL, title="Example", url="https://example.com")
        assert s.type == SourceType.URL
        assert s.url == "https://example.com"

    def test_roundtrip(self):
        s = Source(type=SourceType.DOCUMENT, title="Doc")
        data = s.model_dump()
        s2 = Source.model_validate(data)
        assert s2.title == "Doc"


class TestEvidence:
    def test_relevance_range(self):
        e = Evidence(source_id="abc", quote="test", relevance_score=0.8)
        assert 0.0 <= e.relevance_score <= 1.0

    def test_invalid_relevance(self):
        with pytest.raises(Exception):
            Evidence(source_id="abc", quote="test", relevance_score=1.5)


class TestClaim:
    def test_default_evidence_ids(self):
        c = Claim(content="test claim")
        assert c.evidence_ids == []


class TestAgentMessage:
    def test_collect_request_message(self):
        payload = CollectRequest(task_id="t1", target_products=["P1"])
        msg = AgentMessage(
            from_agent="orchestrator",
            to_agent="collector",
            message_type=MessageType.COLLECT_REQUEST,
            payload=payload,
        )
        assert msg.message_type == MessageType.COLLECT_REQUEST
        assert isinstance(msg.payload, CollectRequest)

    def test_roundtrip_json(self):
        payload = CollectResult(sources=[], coverage_note="done")
        msg = AgentMessage(
            from_agent="collector",
            to_agent="analyst",
            message_type=MessageType.COLLECT_RESULT,
            payload=payload,
        )
        json_str = msg.model_dump_json()
        assert "collect_result" in json_str


# ---------------------------------------------------------------------------
# competitive.py
# ---------------------------------------------------------------------------

class TestFeatureTree:
    def test_nested_tree(self):
        child = FeatureNode(name="Sub", status=FeatureStatus.PARTIAL)
        root = FeatureNode(name="Root", children=[child])
        tree = FeatureTree(product_name="P1", root_nodes=[root])
        assert len(tree.root_nodes[0].children) == 1


class TestPricingModel:
    def test_create(self):
        tier = PricingTier(name="Pro", price=29.99, features=["A", "B"])
        pm = PricingModel(
            product_name="P1",
            model_type=PricingModelType.SUBSCRIPTION,
            tiers=[tier],
        )
        assert pm.tiers[0].price == 29.99


class TestSWOT:
    def test_create(self):
        item = SWOTItem(category=SWOTCategory.STRENGTH, content="Good UX")
        swot = SWOT(product_name="P1", items=[item])
        assert len(swot.items) == 1


class TestPersona:
    def test_create(self):
        p = Persona(segment_name="Enterprise PM", pain_points=["info overload"])
        assert p.segment_name == "Enterprise PM"


# ---------------------------------------------------------------------------
# report.py
# ---------------------------------------------------------------------------

class TestReport:
    def test_nested_sections(self):
        sub = ReportSection(title="Sub", content="detail")
        sec = ReportSection(title="Main", subsections=[sub])
        report = Report(task_id="t1", title="Analysis", sections=[sec])
        assert report.sections[0].subsections[0].title == "Sub"


# ---------------------------------------------------------------------------
# agent.py
# ---------------------------------------------------------------------------

class TestAgentRegistry:
    def test_default_registry_has_four_roles(self):
        assert len(default_registry.roles) == 4

    def test_lookup(self):
        role = default_registry.lookup("collector")
        assert role is not None
        assert role.role_type == RoleType.COLLECTOR

    def test_validate_name(self):
        assert default_registry.validate_name("qa") is True
        assert default_registry.validate_name("nonexistent") is False


# ---------------------------------------------------------------------------
# ratchet.py
# ---------------------------------------------------------------------------

class TestQAIssue:
    def test_create(self):
        issue = QAIssue(
            issue_type=IssueType.MISSING_EVIDENCE,
            description="Claim has no evidence",
            severity=Severity.CRITICAL,
        )
        assert issue.issue_type == IssueType.MISSING_EVIDENCE


class TestConstraintRule:
    def test_create(self):
        issue = QAIssue(
            issue_type=IssueType.MISSING_FIELD,
            description="Missing pricing",
        )
        rule = ConstraintRule(
            source_issue=issue,
            constraint_type="require_field",
            constraint_value="pricing_model",
            applied_to="analyst",
        )
        assert rule.applied_to == "analyst"


class TestTaskMetrics:
    def test_coverage_range(self):
        m = TaskMetrics(task_id="t1", evidence_coverage_rate=0.85)
        assert 0.0 <= m.evidence_coverage_rate <= 1.0


# ---------------------------------------------------------------------------
# trace.py
# ---------------------------------------------------------------------------

class TestTraceEvent:
    def test_create(self):
        e = TraceEvent(agent_name="collector", event_type=EventType.START)
        assert e.event_type == EventType.START


class TestAgentTrace:
    def test_default_status(self):
        t = AgentTrace(agent_name="analyst", task_id="t1")
        assert t.status == TraceStatus.RUNNING
