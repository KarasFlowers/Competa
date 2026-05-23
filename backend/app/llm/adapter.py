"""LLM Adapter — unified interface for language model calls.

Provides BaseLLM abstract interface and MockLLM implementation that returns
deterministic mock data for each schema type, enabling offline DAG execution.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Type, TypeVar

from pydantic import BaseModel

from app.guardrails import GuardrailError, validate_output
from app.schemas.base import (
    CollectResult,
    AnalyzeResult,
    WriteResult,
    QAFeedback,
    Source,
    SourceType,
    MessageType,
)
from app.schemas.competitive import (
    FeatureNode,
    FeatureStatus,
    FeatureTree,
    PricingModel,
    PricingModelType,
    PricingTier,
    Persona,
    SWOT,
    SWOTItem,
    SWOTCategory,
)
from app.schemas.ratchet import (
    QAIssue,
    IssueType,
    Severity,
    ConstraintRule,
)

T = TypeVar("T", bound=BaseModel)


class BaseLLM(ABC):
    """Abstract LLM interface — inspired by CrewAI output_pydantic pattern."""

    @abstractmethod
    async def generate(self, prompt: str, schema_cls: Type[T], **kwargs: Any) -> T:
        """Generate structured output conforming to *schema_cls*.

        Returns a validated Pydantic model instance.
        Raises GuardrailError if the output fails validation after retries.
        """


class MockLLM(BaseLLM):
    """Deterministic mock LLM for offline DAG execution.

    - CollectResult  → 3 simulated sources per call
    - AnalyzeResult  → feature trees, pricing, personas, SWOT per competitor
    - WriteResult    → structured report with sections & claims
    - QAFeedback     → first call returns passed=false (triggers ratchet),
                       second call returns passed=true
    """

    def __init__(self) -> None:
        self._qa_call_count: int = 0

    async def generate(self, prompt: str, schema_cls: Type[T], **kwargs: Any) -> T:
        competitors: list[str] = kwargs.get("competitors", ["CompetitorA", "CompetitorB"])
        target_product: str = kwargs.get("target_product", "TargetProduct")

        if schema_cls is CollectResult:
            data = self._mock_collect(competitors, target_product)
        elif schema_cls is AnalyzeResult:
            data = self._mock_analyze(competitors)
        elif schema_cls is WriteResult:
            sources = kwargs.get("sources", [])
            data = self._mock_write(target_product, competitors, sources)
        elif schema_cls is QAFeedback:
            data = self._mock_qa()
        else:
            raise ValueError(f"MockLLM does not support schema: {schema_cls.__name__}")

        return validate_output(schema_cls, data)

    # ------------------------------------------------------------------
    # Mock data generators
    # ------------------------------------------------------------------

    def _mock_collect(self, competitors: list[str], target_product: str) -> dict:
        products = [target_product] + competitors
        sources = []
        for product in products:
            sources.append({
                "id": uuid.uuid4().hex,
                "type": SourceType.URL.value,
                "url": f"https://example.com/{product.lower().replace(' ', '-')}",
                "title": f"{product} Official Website",
                "content_snippet": f"{product} is a leading solution in this space, "
                                   f"offering comprehensive features for enterprise customers.",
                "fetched_at": datetime.utcnow().isoformat(),
            })
            sources.append({
                "id": uuid.uuid4().hex,
                "type": SourceType.DOCUMENT.value,
                "url": f"https://docs.example.com/{product.lower().replace(' ', '-')}/pricing",
                "title": f"{product} Pricing Documentation",
                "content_snippet": f"{product} offers multiple pricing tiers "
                                   f"ranging from free to enterprise plans.",
                "fetched_at": datetime.utcnow().isoformat(),
            })
        return {
            "message_type": MessageType.COLLECT_RESULT.value,
            "sources": sources,
            "coverage_note": f"Collected {len(sources)} sources covering "
                             f"{len(products)} products.",
        }

    def _mock_analyze(self, competitors: list[str]) -> dict:
        feature_trees = []
        pricing_models = []
        personas = []
        swot_analyses = []

        for comp in competitors:
            feature_trees.append({
                "product_name": comp,
                "root_nodes": [
                    {
                        "name": "Core Features",
                        "description": f"Core capabilities of {comp}",
                        "status": FeatureStatus.SUPPORTED.value,
                        "children": [
                            {"name": "Dashboard", "description": "Analytics dashboard",
                             "status": FeatureStatus.SUPPORTED.value, "children": []},
                            {"name": "API Access", "description": "RESTful API",
                             "status": FeatureStatus.SUPPORTED.value, "children": []},
                            {"name": "Integrations", "description": "Third-party integrations",
                             "status": FeatureStatus.PARTIAL.value, "children": []},
                        ],
                    },
                ],
            })

            pricing_models.append({
                "product_name": comp,
                "model_type": PricingModelType.SUBSCRIPTION.value,
                "tiers": [
                    {"name": "Free", "price": 0, "currency": "USD", "period": "monthly",
                     "features": ["Basic dashboard", "5 projects"],
                     "limitations": ["No API access", "Community support only"]},
                    {"name": "Pro", "price": 29.99, "currency": "USD", "period": "monthly",
                     "features": ["Full dashboard", "Unlimited projects", "API access"],
                     "limitations": ["Standard support"]},
                    {"name": "Enterprise", "price": 99.99, "currency": "USD", "period": "monthly",
                     "features": ["Everything in Pro", "SSO", "Dedicated support"],
                     "limitations": []},
                ],
            })

            personas.append({
                "segment_name": f"{comp} Power Users",
                "demographics": "25-45, tech-savvy professionals",
                "pain_points": ["Complex setup process", "Limited customization"],
                "needs": ["Ease of use", "Scalability", "Good documentation"],
                "product_usage_patterns": "Daily active usage for team collaboration",
            })

            swot_analyses.append({
                "product_name": comp,
                "items": [
                    {"category": SWOTCategory.STRENGTH.value,
                     "content": f"{comp} has strong brand recognition",
                     "evidence_ids": []},
                    {"category": SWOTCategory.WEAKNESS.value,
                     "content": f"{comp} pricing is higher than average",
                     "evidence_ids": []},
                    {"category": SWOTCategory.OPPORTUNITY.value,
                     "content": "Growing market demand for AI-powered analytics",
                     "evidence_ids": []},
                    {"category": SWOTCategory.THREAT.value,
                     "content": "New entrants with competitive pricing",
                     "evidence_ids": []},
                ],
            })

        return {
            "message_type": MessageType.ANALYZE_RESULT.value,
            "feature_trees": feature_trees,
            "pricing_models": pricing_models,
            "personas": personas,
            "swot_analyses": swot_analyses,
        }

    def _mock_write(
        self,
        target_product: str,
        competitors: list[str],
        sources: list[Any],
    ) -> dict:
        source_ids = [s["id"] if isinstance(s, dict) else s.id for s in sources[:3]] if sources else []
        evidence_id_1 = uuid.uuid4().hex
        evidence_id_2 = uuid.uuid4().hex

        report = {
            "id": uuid.uuid4().hex,
            "task_id": "",
            "title": f"{target_product} Competitive Analysis Report",
            "executive_summary": (
                f"This report provides a comprehensive competitive analysis of "
                f"{target_product} against {', '.join(competitors)}. "
                f"Key findings include differences in feature coverage, pricing strategy, "
                f"and target user segments."
            ),
            "sections": [
                {
                    "title": "Feature Comparison",
                    "content": (
                        f"A detailed comparison of core features across {target_product} "
                        f"and its competitors reveals several areas of differentiation."
                    ),
                    "claims": [
                        {
                            "id": uuid.uuid4().hex,
                            "content": f"{target_product} offers superior API access compared to competitors.",
                            "evidence_ids": [evidence_id_1] if source_ids else [],
                            "confidence": 0.8,
                            "category": "features",
                        },
                    ],
                    "subsections": [],
                },
                {
                    "title": "Pricing Analysis",
                    "content": "Pricing comparison shows varied strategies across competitors.",
                    "claims": [
                        {
                            "id": uuid.uuid4().hex,
                            "content": "Enterprise tier pricing varies significantly, "
                                       "with a range of $50-$150/month.",
                            "evidence_ids": [evidence_id_2] if source_ids else [],
                            "confidence": 0.75,
                            "category": "pricing",
                        },
                    ],
                    "subsections": [],
                },
                {
                    "title": "SWOT Summary",
                    "content": (
                        f"SWOT analysis reveals that {target_product} has strong technical "
                        f"capabilities but faces pricing pressure from new entrants."
                    ),
                    "claims": [],
                    "subsections": [],
                },
            ],
            "generated_at": datetime.utcnow().isoformat(),
        }

        return {
            "message_type": MessageType.WRITE_RESULT.value,
            "report": report,
        }

    def _mock_qa(self) -> dict:
        self._qa_call_count += 1

        if self._qa_call_count <= 1:
            issue = QAIssue(
                issue_type=IssueType.MISSING_EVIDENCE,
                field_path="sections[0].claims",
                description="功能对比分析 section 中的 Claims 缺少 evidence_ids 引用，"
                            "无法追溯结论来源。",
                severity=Severity.CRITICAL,
            )
            constraint = ConstraintRule(
                source_issue=issue,
                constraint_type="require_evidence",
                constraint_value="功能对比分析 section 的每个 Claim 必须引用至少 1 个有效来源 ID",
                applied_to="writer",
            )
            return {
                "message_type": MessageType.QA_FEEDBACK.value,
                "passed": False,
                "issues": [issue.model_dump()],
                "retry_target": "write",
                "constraints": [constraint.model_dump()],
            }
        else:
            return {
                "message_type": MessageType.QA_FEEDBACK.value,
                "passed": True,
                "issues": [],
                "retry_target": "",
                "constraints": [],
            }
