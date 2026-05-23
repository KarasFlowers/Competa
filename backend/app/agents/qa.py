"""QA Agent — validates report quality, triggers ratchet mechanism."""

from __future__ import annotations

import json
from typing import Any, Type

from pydantic import BaseModel

from app.agents.base import BaseAgent
from app.schemas.base import QAFeedback


class QAAgent(BaseAgent):
    name = "qa"
    role = "质检审核员"
    goal = "校验报告的完整性、引用完整性和内容质量，不合格时给出具体修改指令"
    backstory = (
        "你是一位严谨的质量审核专家，负责确保竞品分析报告的每条结论"
        "都有可靠来源支撑，内容深度足够，不允许敷衍或无证据的断言进入最终报告。"
    )

    def _get_output_schema(self) -> Type[BaseModel]:
        return QAFeedback

    def _build_prompt(self, state: dict[str, Any]) -> str:
        report = state.get("report", {})
        sources = state.get("sources", [])
        retry_count = state.get("retry_count", 0)

        # Format report content for review
        report_text = self._format_report_for_review(report)
        # Format sources for cross-reference check
        source_ids = self._extract_source_ids(sources)

        parts = [
            self._build_role_context(),
            "",
            "## 任务",
            f"审核以下竞品分析报告（第 {retry_count + 1} 轮审核）。",
            "",
            "## 待审核的报告内容",
            "",
            report_text,
            "",
            "## 可用的来源 ID 列表",
            f"共 {len(source_ids)} 个有效来源 ID：",
            ", ".join(source_ids) if source_ids else "（无来源）",
            "",
            "## 审核标准",
            "",
            "逐项检查以下标准，如有不达标项则 passed=false：",
            "",
            "### 1. 内容深度",
            "- executive_summary 是否至少 200 字（中文字符）？",
            "- sections 是否至少 4 个？",
            "- 每个 section 的 content 是否至少 100 字？",
            "- 内容是否包含具体数据和事实，而非空洞描述？",
            "",
            "### 2. 引用完整性",
            "- 每个 Claim 的 evidence_ids 是否非空？",
            "- evidence_ids 中的 ID 是否存在于上面的来源 ID 列表中？",
            "- 是否存在无证据支撑的断言？",
            "",
            "### 3. 结构完整性",
            "- title 是否存在且有意义？",
            "- sections 是否覆盖功能对比、定价分析、用户画像、SWOT？",
            "- 每个 section 是否有 claims？",
            "",
            "### 4. 竞品覆盖度",
            "- 报告是否涵盖了所有目标竞品？",
            "- 对比分析是否涉及多个产品？",
            "",
            "## 输出要求",
            "",
            "如果所有标准都达标：",
            "- passed: true",
            "- issues: []",
            "- retry_target: \"\"",
            "- constraints: []",
            "",
            "如果有不达标项：",
            "- passed: false",
            "- issues: 列出每个具体问题（issue_type, field_path, description, severity）",
            "- retry_target: 建议打回到哪个 Agent (\"write\" 表示重新写报告，\"collect\" 表示需要更多数据)",
            "- constraints: 为每个 issue 生成一条 ConstraintRule，包含：",
            "  - source_issue: 对应的 QAIssue 对象",
            "  - constraint_type: 约束类型（如 min_length, require_evidence, require_section）",
            "  - constraint_value: 具体的修改指令（自然语言，要具体）",
            "  - applied_to: 目标 Agent（通常是 \"writer\"）",
            "",
            "**重要**: constraint_value 必须是具体可执行的指令，例如：",
            "- \"功能对比分析 section 的 content 至少增加到 400 字，包含具体功能名称\"",
            "- \"为 Claim '定价差异显著' 添加引用真实来源 ID\"",
            "- \"增加 SWOT 综合评估与建议 section\"",
        ]

        constraints_ctx = self._build_constraints_context(state)
        if constraints_ctx:
            parts.extend([
                "",
                "## 上轮 QA 约束（检查是否已修正）",
                "以下是上次审核提出的约束，请验证是否已经被修正：",
                constraints_ctx,
            ])

        return "\n".join(parts)

    def _format_report_for_review(self, report: dict[str, Any] | None) -> str:
        """Format report content for QA review."""
        if not report:
            return "（报告为空 — 严重问题）"

        # report might be wrapped in {"message_type": ..., "report": {...}}
        inner = report.get("report", report) if isinstance(report, dict) else report
        if not isinstance(inner, dict):
            return f"（报告格式异常: {type(inner)}）"

        parts = []

        title = inner.get("title", "")
        parts.append(f"**标题**: {title}")
        parts.append("")

        summary = inner.get("executive_summary", "")
        parts.append(f"**执行摘要** ({len(summary)} 字):")
        parts.append(summary[:500] if summary else "（空）")
        parts.append("")

        sections = inner.get("sections", [])
        parts.append(f"**Sections** (共 {len(sections)} 个):")
        for i, sec in enumerate(sections, 1):
            if isinstance(sec, dict):
                sec_title = sec.get("title", "无标题")
                sec_content = sec.get("content", "")
                claims = sec.get("claims", [])
                parts.append(f"  {i}. {sec_title} ({len(sec_content)} 字, {len(claims)} claims)")
                # Show claims evidence status
                for j, claim in enumerate(claims, 1):
                    if isinstance(claim, dict):
                        evidence = claim.get("evidence_ids", [])
                        parts.append(f"     Claim {j}: \"{claim.get('content', '')[:60]}...\" evidence_ids={evidence}")

        return "\n".join(parts)

    def _extract_source_ids(self, sources: list[dict[str, Any] | Any]) -> list[str]:
        """Extract all source IDs for cross-reference validation."""
        ids = []
        for src in sources:
            if isinstance(src, dict):
                src_id = src.get("id", "")
            else:
                src_id = getattr(src, "id", "")
            if src_id:
                ids.append(src_id)
        return ids

    def _get_llm_kwargs(self, state: dict[str, Any]) -> dict[str, Any]:
        return {
            "competitors": state.get("competitors", []),
            "target_product": state.get("target_product", ""),
        }

    def _extract_state_updates(self, output: BaseModel, state: dict[str, Any]) -> dict[str, Any]:
        result: QAFeedback = output  # type: ignore[assignment]
        updates: dict[str, Any] = {
            "qa_feedback": result.model_dump(),
        }

        # Ratchet mechanism: accumulate constraints across retries
        if not result.passed and result.constraints:
            existing = state.get("constraints", [])
            new_constraints = [
                c.model_dump() if hasattr(c, "model_dump") else c
                for c in result.constraints
            ]
            updates["constraints"] = existing + new_constraints
            updates["retry_count"] = state.get("retry_count", 0) + 1

        return updates
