"""Writer Agent — generates structured competitive analysis report."""

from __future__ import annotations

import json
from typing import Any, Type

from pydantic import BaseModel

from app.agents.base import BaseAgent
from app.schemas.base import WriteResult


class WriterAgent(BaseAgent):
    name = "writer"
    role = "报告撰写专家"
    goal = "基于结构化分析结果生成带引用来源的高质量竞品分析报告"
    backstory = (
        "你是一位专业的商业报告撰写者，擅长将复杂的分析结果"
        "转化为清晰、有说服力的结构化报告。你的报告以深度、数据支撑和可操作性著称。"
    )

    def _get_output_schema(self) -> Type[BaseModel]:
        return WriteResult

    def _build_prompt(self, state: dict[str, Any]) -> str:
        target = state.get("target_product", "")
        competitors = state.get("competitors", [])
        analysis = state.get("analysis", {})
        sources = state.get("sources", [])

        # Format sources reference table
        sources_ref = self._format_sources_reference(sources)
        # Format analysis summary
        analysis_text = self._format_analysis(analysis)

        parts = [
            self._build_role_context(),
            "",
            "## 任务",
            f"基于结构化分析结果，为「{target}」撰写一份完整的竞品分析报告。",
            f"- 目标产品：{target}",
            f"- 竞品：{', '.join(competitors)}",
            "",
            "## 可引用的信息来源",
            "以下来源 ID 可在 claims 的 evidence_ids 中引用：",
            "",
            sources_ref,
            "",
            "## 分析师提供的结构化分析结果",
            "基于以下分析数据撰写报告：",
            "",
            analysis_text,
            "",
            "## 报告结构要求",
            "",
            "输出的 report 字段必须包含：",
            "",
            "### 1. title",
            f"报告标题，包含「{target}」和竞品名",
            "",
            "### 2. executive_summary",
            "- **至少 300 字**的执行摘要",
            "- 概述主要发现、关键差异、核心建议",
            "- 语言专业、直接，面向决策者",
            "",
            "### 3. sections (至少 4 个)",
            "",
            "**Section 1: 功能对比分析**",
            "- content: 至少 400 字，详细对比各产品核心功能差异",
            "- claims: 至少 3 条具体结论，每条都要有 evidence_ids",
            "",
            "**Section 2: 定价策略分析**",
            "- content: 至少 300 字，对比定价模式、价格区间、性价比",
            "- claims: 至少 2 条具体结论",
            "",
            "**Section 3: 用户画像与市场定位**",
            "- content: 至少 300 字，分析目标用户差异和市场策略",
            "- claims: 至少 2 条具体结论",
            "",
            "**Section 4: SWOT 综合评估与建议**",
            "- content: 至少 400 字，综合 SWOT 给出战略建议",
            "- claims: 至少 2 条可操作建议",
            "",
            "### 4. generated_at",
            "当前时间的 ISO 格式字符串",
            "",
            "## 质量要求",
            "- 每个 Claim 的 evidence_ids 必须引用上面来源列表中的真实 ID",
            "- 每个 Claim 的 confidence 反映证据强度 (0.0-1.0)",
            "- 内容必须基于分析数据，不要编造数据",
            "- 语言专业、具体，包含数字和事实",
            "- 避免空洞的描述性语言",
        ]

        constraints_ctx = self._build_constraints_context(state)
        if constraints_ctx:
            parts.extend(["", "## QA 约束（上次被打回的原因，必须修正）", constraints_ctx])

        return "\n".join(parts)

    def _format_sources_reference(self, sources: list[dict[str, Any] | Any]) -> str:
        """Format sources as a concise reference table with IDs."""
        if not sources:
            return "（暂无来源数据）"

        lines = []
        for i, src in enumerate(sources, 1):
            if isinstance(src, dict):
                src_id = src.get("id", f"source_{i}")
                title = src.get("title", "无标题")
                snippet = src.get("content_snippet", "")[:200]
            else:
                src_id = getattr(src, "id", f"source_{i}")
                title = getattr(src, "title", "无标题")
                snippet = getattr(src, "content_snippet", "")[:200]

            lines.append(f"- **[{src_id}]** {title}: {snippet}")

        return "\n".join(lines)

    def _format_analysis(self, analysis: dict[str, Any] | None) -> str:
        """Format analysis results for prompt injection."""
        if not analysis:
            return "（暂无分析数据）"

        parts = []

        # Feature trees
        feature_trees = analysis.get("feature_trees", [])
        if feature_trees:
            parts.append("### 功能树分析")
            for ft in feature_trees:
                name = ft.get("product_name", "")
                nodes = ft.get("root_nodes", [])
                parts.append(f"**{name}**: {len(nodes)} 个核心功能类别")
                for node in nodes[:8]:
                    status = node.get("status", "")
                    children = node.get("children", [])
                    parts.append(f"  - {node.get('name', '')}: [{status}] ({len(children)} 子功能)")
            parts.append("")

        # Pricing models
        pricing = analysis.get("pricing_models", [])
        if pricing:
            parts.append("### 定价模型")
            for pm in pricing:
                name = pm.get("product_name", "")
                model_type = pm.get("model_type", "")
                tiers = pm.get("tiers", [])
                parts.append(f"**{name}** ({model_type}):")
                for tier in tiers:
                    parts.append(f"  - {tier.get('name', '')}: {tier.get('price', 0)} {tier.get('currency', 'USD')}/{tier.get('period', 'month')}")
            parts.append("")

        # Personas
        personas = analysis.get("personas", [])
        if personas:
            parts.append("### 用户画像")
            for p in personas:
                parts.append(f"**{p.get('segment_name', '')}**: {p.get('demographics', '')}")
                pain_points = p.get("pain_points", [])
                if pain_points:
                    parts.append(f"  痛点: {', '.join(pain_points[:5])}")
            parts.append("")

        # SWOT
        swots = analysis.get("swot_analyses", [])
        if swots:
            parts.append("### SWOT 分析")
            for s in swots:
                name = s.get("product_name", "")
                items = s.get("items", [])
                parts.append(f"**{name}**:")
                for item in items:
                    parts.append(f"  - [{item.get('category', '')}] {item.get('content', '')[:80]}")
            parts.append("")

        return "\n".join(parts) if parts else "（分析数据为空）"

    def _get_llm_kwargs(self, state: dict[str, Any]) -> dict[str, Any]:
        return {
            "competitors": state.get("competitors", []),
            "target_product": state.get("target_product", ""),
            "sources": state.get("sources", []),
        }

    def _extract_state_updates(self, output: BaseModel, state: dict[str, Any]) -> dict[str, Any]:
        result: WriteResult = output  # type: ignore[assignment]
        return {
            "report": result.model_dump(),
        }
