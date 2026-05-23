"""Analyst Agent — extracts feature trees, pricing, personas, SWOT."""

from __future__ import annotations

import json
from typing import Any, Type

from pydantic import BaseModel

from app.agents.base import BaseAgent
from app.schemas.base import AnalyzeResult


class AnalystAgent(BaseAgent):
    name = "analyst"
    role = "竞品分析师"
    goal = "基于采集数据提取结构化竞品洞察：功能树、定价模型、用户画像、SWOT"
    backstory = (
        "你是一位资深的产品分析师，擅长从非结构化信息中提取"
        "结构化的竞品洞察。你的分析必须基于实际数据，不允许凭空捏造。"
    )

    def _get_output_schema(self) -> Type[BaseModel]:
        return AnalyzeResult

    def _build_prompt(self, state: dict[str, Any]) -> str:
        sources = state.get("sources", [])
        competitors = state.get("competitors", [])
        target = state.get("target_product", "")
        products = [target] + competitors

        # Serialize sources into prompt
        sources_text = self._format_sources(sources)

        parts = [
            self._build_role_context(),
            "",
            "## 任务",
            f"基于以下采集到的信息源，对目标产品「{target}」及其竞品进行结构化分析。",
            f"- 目标产品：{target}",
            f"- 竞品：{', '.join(competitors)}",
            "",
            "## 采集到的信息源数据",
            "以下是 Collector 采集到的原始数据，你的分析**必须基于这些数据**：",
            "",
            sources_text,
            "",
            "## 分析要求",
            f"为每个产品（{', '.join(products)}）提取：",
            "",
            "### 1. 功能树 (feature_trees)",
            "- 每个产品一个 FeatureTree",
            "- 每个 FeatureTree 至少包含 5 个 root_nodes（核心功能类别）",
            "- 每个 root_node 至少 2 个 children（子功能）",
            "- status 标注为 supported/partial/missing",
            "",
            "### 2. 定价模型 (pricing_models)",
            "- 每个产品一个 PricingModel",
            "- model_type: freemium/subscription/one_time/usage_based",
            "- 至少列出 2-3 个定价层级 (tiers)，包含具体价格",
            "",
            "### 3. 用户画像 (personas)",
            "- 至少 2 个目标用户群体",
            "- 每个 persona 包含 demographics、pain_points (>=3)、needs (>=3)",
            "",
            "### 4. SWOT 分析 (swot_analyses)",
            "- 每个产品一个 SWOT",
            "- 每个类别 (strength/weakness/opportunity/threat) 至少 2 条",
            "- 每条 content 至少 30 字，包含具体描述",
            "",
            "## 质量要求",
            "- 所有分析必须基于上面提供的信息源数据，不要编造不存在的信息",
            "- 如果某个维度数据不足，在 content 中标注「基于有限信息推断」",
            "- 描述要具体，避免泛泛的形容词",
        ]

        constraints_ctx = self._build_constraints_context(state)
        if constraints_ctx:
            parts.extend(["", "## QA 约束（必须遵循）", constraints_ctx])

        return "\n".join(parts)

    def _format_sources(self, sources: list[dict[str, Any] | Any]) -> str:
        """Format sources into readable text for prompt injection."""
        if not sources:
            return "（暂无采集数据）"

        lines = []
        for i, src in enumerate(sources, 1):
            if isinstance(src, dict):
                title = src.get("title", "无标题")
                snippet = src.get("content_snippet", "")
                url = src.get("url", "")
                src_id = src.get("id", f"source_{i}")
            else:
                title = getattr(src, "title", "无标题")
                snippet = getattr(src, "content_snippet", "")
                url = getattr(src, "url", "")
                src_id = getattr(src, "id", f"source_{i}")

            lines.append(f"### 来源 {i} [ID: {src_id}]")
            lines.append(f"**标题**: {title}")
            if url:
                lines.append(f"**链接**: {url}")
            lines.append(f"**内容**: {snippet}")
            lines.append("")

        return "\n".join(lines)

    def _get_llm_kwargs(self, state: dict[str, Any]) -> dict[str, Any]:
        return {
            "competitors": state.get("competitors", []),
            "target_product": state.get("target_product", ""),
        }

    def _extract_state_updates(self, output: BaseModel, state: dict[str, Any]) -> dict[str, Any]:
        result: AnalyzeResult = output  # type: ignore[assignment]
        return {
            "analysis": result.model_dump(),
        }
