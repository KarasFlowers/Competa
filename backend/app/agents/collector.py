"""Collector Agent — gathers information from multiple sources."""

from __future__ import annotations

import json
from typing import Any, Type

from pydantic import BaseModel

from app.agents.base import BaseAgent
from app.schemas.base import CollectResult


class CollectorAgent(BaseAgent):
    name = "collector"
    role = "信息采集专员"
    goal = "从多源采集目标产品和竞品的公开信息，确保信息全面、具体、可引用"
    backstory = (
        "你是一位经验丰富的市场调研员，擅长从官方网站、文档、"
        "行业报告等渠道快速获取产品相关信息。你注重信息的具体性和可验证性。"
    )

    def _get_output_schema(self) -> Type[BaseModel]:
        return CollectResult

    def _build_prompt(self, state: dict[str, Any]) -> str:
        target = state.get("target_product", "")
        competitors = state.get("competitors", [])
        industry = state.get("industry", "")
        products = [target] + competitors

        parts = [
            self._build_role_context(),
            "",
            "## 任务",
            f"为以下产品采集竞品分析所需的公开信息：",
            f"- 目标产品：{target}",
            f"- 竞品：{', '.join(competitors)}",
            f"- 行业：{industry or '通用'}",
            "",
            "## 采集要求",
            f"为每个产品（共 {len(products)} 个）采集 **至少 3 条**信息源，总共至少 {len(products) * 3} 条。",
            "",
            "每条信息源必须包含：",
            "1. **type**: 来源类型 (url/document/interview/survey)",
            "2. **url**: 来源链接（如适用）",
            "3. **title**: 来源标题，明确标注是哪个产品的什么信息",
            "4. **content_snippet**: 至少 150 字的具体内容摘要，包含：",
            "   - 产品的核心功能描述",
            "   - 具体的定价数据（如有）",
            "   - 用户评价或市场数据（如有）",
            "   - 技术架构或差异化特点",
            "",
            "## 信息维度",
            "确保为每个产品覆盖以下维度：",
            "- 产品官网/文档（核心功能、特色）",
            "- 定价页面（套餐、价格、限制）",
            "- 用户评价/行业报告（口碑、市场定位）",
            "",
            "## 输出质量标准",
            "- content_snippet 必须包含**具体事实和数据**，不要泛泛而谈",
            "- 不同来源之间内容不要重复",
            "- coverage_note 字段概述采集覆盖情况和可能的信息缺口",
        ]

        constraints_ctx = self._build_constraints_context(state)
        if constraints_ctx:
            parts.extend(["", "## QA 约束（必须遵循）", constraints_ctx])

        return "\n".join(parts)

    def _get_llm_kwargs(self, state: dict[str, Any]) -> dict[str, Any]:
        return {
            "competitors": state.get("competitors", []),
            "target_product": state.get("target_product", ""),
        }

    def _extract_state_updates(self, output: BaseModel, state: dict[str, Any]) -> dict[str, Any]:
        result: CollectResult = output  # type: ignore[assignment]
        return {
            "sources": [s.model_dump() for s in result.sources],
        }
