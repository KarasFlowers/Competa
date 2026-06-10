"""Mock LLM client — returns preset JSON for each agent, no API key needed.

Enabled via LLM_MOCK=true environment variable.
"""

from __future__ import annotations

import asyncio
import json
import time

from app.llm.client import LLMResponse

# Track QA call count so first call fails and second passes
_qa_call_counts: dict[str, int] = {}


def _collector_response() -> str:
    return json.dumps({
        "sources": [
            {
                "type": "url",
                "url": "https://www.notion.so/pricing",
                "title": "Notion Pricing Page",
                "content_snippet": "Notion offers Free, Plus ($8/mo), Business ($15/mo), and Enterprise plans. Free tier includes 1 workspace, limited blocks.",
            },
            {
                "type": "document",
                "url": None,
                "title": "Product Comparison Whitepaper 2024",
                "content_snippet": "Notion excels in all-in-one workspace flexibility. Obsidian focuses on local-first markdown knowledge graphs. Roam Research targets bidirectional linking researchers.",
            },
            {
                "type": "interview",
                "url": None,
                "title": "Interview: Product Manager at Tech Startup",
                "content_snippet": "We chose Notion for team collaboration but power users prefer Obsidian for personal knowledge management due to speed and plugin ecosystem.",
            },
            {
                "type": "survey",
                "url": None,
                "title": "User Satisfaction Survey Q1 2024",
                "content_snippet": "Notion: 4.2/5 ease of use, 3.8/5 performance. Obsidian: 3.5/5 ease of use, 4.7/5 performance. Roam: 3.0/5 ease of use, 3.5/5 performance.",
            },
        ],
        "coverage_note": "Covered pricing, feature comparison, user feedback across all three products.",
    })


def _analyst_response() -> str:
    return json.dumps({
        "feature_trees": [
            {
                "product_name": "Notion",
                "root_nodes": [
                    {"name": "Collaboration", "description": "Real-time team editing and comments", "status": "supported", "children": []},
                    {"name": "Databases", "description": "Relational databases with multiple views", "status": "supported", "children": []},
                    {"name": "API & Integrations", "description": "REST API and third-party integrations", "status": "partial", "children": []},
                ],
            },
            {
                "product_name": "Obsidian",
                "root_nodes": [
                    {"name": "Local-First Storage", "description": "Markdown files stored locally", "status": "supported", "children": []},
                    {"name": "Plugin Ecosystem", "description": "Community plugins via API", "status": "supported", "children": []},
                    {"name": "Collaboration", "description": "Real-time sync via Obsidian Sync (paid)", "status": "partial", "children": []},
                ],
            },
        ],
        "pricing_models": [
            {
                "product_name": "Notion",
                "model_type": "freemium",
                "tiers": [
                    {"name": "Free", "price": 0, "currency": "USD", "period": "monthly", "features": ["1 workspace", "Limited blocks"], "limitations": ["No admin tools"]},
                    {"name": "Plus", "price": 8, "currency": "USD", "period": "monthly", "features": ["Unlimited blocks", "30 day history"], "limitations": ["No SAML SSO"]},
                ],
            },
            {
                "product_name": "Obsidian",
                "model_type": "freemium",
                "tiers": [
                    {"name": "Personal", "price": 0, "currency": "USD", "period": "monthly", "features": ["Local vault", "Core plugins"], "limitations": ["No sync"]},
                    {"name": "Sync", "price": 4, "currency": "USD", "period": "monthly", "features": ["End-to-end encryption", "Version history"], "limitations": ["1GB storage"]},
                ],
            },
        ],
        "personas": [
            {
                "segment_name": "Team Collaborators",
                "demographics": "25-40, knowledge workers in tech companies",
                "pain_points": ["Scattered information", "Poor cross-team visibility"],
                "needs": ["Centralized workspace", "Real-time collaboration"],
                "product_usage_patterns": "Daily Notion users, occasional Obsidian for personal notes",
            },
            {
                "segment_name": "Power Researchers",
                "demographics": "22-35, academics and researchers",
                "pain_points": ["Linking related concepts", "Long-form knowledge management"],
                "needs": ["Bidirectional linking", "Local data control"],
                "product_usage_patterns": "Obsidian for personal PKM, Roam for research projects",
            },
        ],
        "swot_analyses": [
            {
                "product_name": "Notion",
                "items": [
                    {"category": "strength", "content": "All-in-one workspace with databases and collaboration", "evidence_ids": []},
                    {"category": "weakness", "content": "Performance issues with large workspaces", "evidence_ids": []},
                    {"category": "opportunity", "content": "Growing enterprise market for knowledge management", "evidence_ids": []},
                    {"category": "threat", "content": "Obsidian gaining traction with privacy-conscious users", "evidence_ids": []},
                ],
            },
        ],
    })


def _writer_response() -> str:
    return json.dumps({
        "title": "Competitive Analysis: Notion vs Obsidian vs Roam Research",
        "executive_summary": "Notion leads in team collaboration and all-in-one workspace features, while Obsidian excels in local-first personal knowledge management. Roam Research targets academic researchers with bidirectional linking but faces usability challenges.",
        "sections": [
            {
                "title": "Feature Comparison",
                "content": "Notion offers the most comprehensive feature set for team collaboration with real-time editing, databases, and integrations. Obsidian focuses on local-first markdown with a rich plugin ecosystem.",
                "claims": [
                    {"id": "claim_1", "content": "Notion supports real-time collaboration across all pricing tiers", "evidence_ids": ["src_1"], "confidence": 0.9, "category": "feature"},
                    {"id": "claim_2", "content": "Obsidian provides 1000+ community plugins for customization", "evidence_ids": ["src_2"], "confidence": 0.85, "category": "feature"},
                ],
                "subsections": [],
            },
            {
                "title": "Pricing Analysis",
                "content": "Notion uses a freemium model with paid tiers starting at $8/month. Obsidian's core is free with paid sync and publish add-ons.",
                "claims": [
                    {"id": "claim_3", "content": "Notion Plus plan costs $8/month per user", "evidence_ids": ["src_1"], "confidence": 0.95, "category": "pricing"},
                    {"id": "claim_4", "content": "Obsidian Sync costs $4/month with end-to-end encryption", "evidence_ids": ["src_2"], "confidence": 0.9, "category": "pricing"},
                ],
                "subsections": [],
            },
            {
                "title": "User Personas",
                "content": "Two primary personas emerge: Team Collaborators who prefer Notion, and Power Researchers who prefer Obsidian or Roam.",
                "claims": [
                    {"id": "claim_5", "content": "Team collaborators rate Notion 4.2/5 for ease of use", "evidence_ids": ["src_4"], "confidence": 0.8, "category": "persona"},
                    {"id": "claim_6", "content": "Power researchers prefer Obsidian for personal knowledge management", "evidence_ids": ["src_3"], "confidence": 0.85, "category": "persona"},
                ],
                "subsections": [],
            },
            {
                "title": "SWOT Analysis: Notion",
                "content": "Notion's strengths in collaboration are offset by performance concerns with large workspaces.",
                "claims": [
                    {"id": "claim_7", "content": "Notion's all-in-one workspace is a key strength for enterprise adoption", "evidence_ids": ["src_2"], "confidence": 0.85, "category": "swot"},
                    {"id": "claim_8", "content": "Performance issues in large workspaces remain a weakness", "evidence_ids": ["src_4"], "confidence": 0.75, "category": "swot"},
                ],
                "subsections": [],
            },
            {
                "title": "Conclusions & Recommendations",
                "content": "For team-heavy organizations, Notion remains the best choice. For individual knowledge workers prioritizing speed and privacy, Obsidian is superior.",
                "claims": [
                    {"id": "claim_9", "content": "Notion is recommended for team collaboration scenarios", "evidence_ids": ["src_1", "src_3"], "confidence": 0.9, "category": "conclusion"},
                    {"id": "claim_10", "content": "Obsidian is recommended for privacy-conscious individual users", "evidence_ids": ["src_3", "src_4"], "confidence": 0.85, "category": "conclusion"},
                ],
                "subsections": [],
            },
        ],
    })


def _fieldwork_response() -> str:
    return json.dumps({
        "survey_results": [
            {
                "persona": "Team Collaborators",
                "respondent_count": 180,
                "answers": [
                    {"question_id": "q1", "dimension": "feature", "answer": "68% rank real-time collaboration as the top deciding factor"},
                    {"question_id": "q2", "dimension": "pricing", "answer": "54% find $8/mo acceptable, 31% want a cheaper team tier"},
                ],
                "key_findings": [
                    "Collaboration features outweigh price for team buyers",
                    "A mid-tier price gap is an opening for competitors",
                ],
            },
            {
                "persona": "Power Researchers",
                "respondent_count": 120,
                "answers": [
                    {"question_id": "q3", "dimension": "performance", "answer": "72% cite speed and local-first storage as must-haves"},
                ],
                "key_findings": ["Performance and data ownership drive Obsidian preference"],
            },
        ],
        "interview_transcripts": [
            {
                "persona": "Team Collaborators",
                "excerpts": [
                    {
                        "question_id": "iq1", "dimension": "switching",
                        "quote": "We tried moving off Notion but the databases keep us locked in.",
                        "insight": "Database depth creates switching costs that protect Notion",
                    },
                ],
                "key_findings": ["Notion's databases are a retention moat"],
            },
        ],
        "summary": "Simulated fieldwork confirms collaboration depth retains team users while "
                   "performance-sensitive researchers favor local-first tools — a mid-tier "
                   "price gap is the clearest competitive opening.",
    })


def _qa_response(task_id: str) -> str:
    """First QA call returns failed (to demonstrate retry), second returns passed."""
    global _qa_call_counts
    count = _qa_call_counts.get(task_id, 0) + 1
    _qa_call_counts[task_id] = count

    # Prevent unbounded growth: clean up old entries
    if len(_qa_call_counts) > 100:
        _qa_call_counts = {task_id: count}

    if count == 1:
        return json.dumps({
            "passed": False,
            "issues": [
                {
                    "issue_type": "low_coverage",
                    "field_path": "sources",
                    "description": "Only 4 sources collected, need more coverage for Roam Research",
                    "severity": "warning",
                },
            ],
            "metrics": {
                "source_count": 4,
                "claim_count": 8,
                "claims_with_evidence": 8,
                "evidence_coverage_rate": 1.0,
            },
            "summary": "Report is mostly complete but source coverage for Roam Research is insufficient.",
        })
    else:
        return json.dumps({
            "passed": True,
            "issues": [],
            "metrics": {
                "source_count": 6,
                "claim_count": 10,
                "claims_with_evidence": 10,
                "evidence_coverage_rate": 1.0,
            },
            "summary": "All checks passed after retry.",
        })


def _survey_response() -> str:
    return json.dumps({
        "title": "用户竞品认知与使用偏好调研",
        "description": "本问卷旨在了解目标用户对协同办公产品的认知、使用习惯及切换意愿，为竞品分析提供一手用户数据。",
        "questions": [
            {
                "id": "q1",
                "text": "您目前主要使用哪款协同办公工具？",
                "type": "single_choice",
                "options": ["飞书", "钉钉", "企业微信", "Notion", "其他"],
                "dimension": "usage",
            },
            {
                "id": "q2",
                "text": "您选择该工具的最主要原因是什么？",
                "type": "single_choice",
                "options": ["功能丰富", "价格合理", "团队习惯", "生态集成", "用户体验", "其他"],
                "dimension": "decision_factor",
            },
            {
                "id": "q3",
                "text": "您对当前使用的工具最不满意的地方是？",
                "type": "open_ended",
                "options": [],
                "dimension": "pain_point",
            },
            {
                "id": "q4",
                "text": "如果有一款新工具能解决您的痛点，您愿意切换吗？",
                "type": "single_choice",
                "options": ["非常愿意", "可以考虑", "不太愿意", "完全不愿意"],
                "dimension": "switching_intent",
            },
            {
                "id": "q5",
                "text": "请对以下功能按重要性排序（1-5，1为最重要）",
                "type": "ranking",
                "options": ["即时通讯", "文档协作", "视频会议", "项目管理", "日历与日程"],
                "dimension": "feature_priority",
            },
        ],
        "target_audience": "25-45岁知识工作者，团队规模10-500人，使用协同办公工具6个月以上",
        "estimated_duration_min": 5,
    })


def _interview_response() -> str:
    return json.dumps({
        "title": "协同办公工具用户深度访谈提纲",
        "target_persona": "团队管理者 / 重度用户",
        "opening_script": "感谢您抽出时间参与本次访谈。我们想了解您在日常工作中使用协同办公工具的体验，包括您喜欢的方面和遇到的困难。本次访谈大约需要30分钟，过程中没有对错之分，请畅所欲言。",
        "questions": [
            {
                "id": "iq1",
                "phase": "opening",
                "text": "请简单介绍一下您的日常工作流程，以及协同办公工具在其中的角色。",
                "follow_ups": ["您一天中大概有多少时间在使用这些工具？", "和其他团队成员的协作频率如何？"],
                "target_persona": "团队管理者",
                "dimension": "context",
            },
            {
                "id": "iq2",
                "phase": "core",
                "text": "在使用当前工具的过程中，有没有遇到过让您特别头疼的场景？",
                "follow_ups": ["能举一个具体的例子吗？", "您当时是如何解决的？", "这个问题多久出现一次？"],
                "target_persona": "团队管理者",
                "dimension": "pain_point",
            },
            {
                "id": "iq3",
                "phase": "core",
                "text": "您是否考虑过切换到其他协同办公工具？是什么促使您有（或没有）这个想法？",
                "follow_ups": ["您评估过哪些替代方案？", "最大的顾虑是什么？", "迁移成本中哪个部分最让您担心？"],
                "target_persona": "团队管理者",
                "dimension": "switching",
            },
            {
                "id": "iq4",
                "phase": "probing",
                "text": "如果让您给当前工具的产品经理提三个改进建议，您会说什么？",
                "follow_ups": ["为什么是这三个？", "如果只能实现一个，您选哪个？"],
                "target_persona": "重度用户",
                "dimension": "improvement",
            },
            {
                "id": "iq5",
                "phase": "closing",
                "text": "还有什么想补充的，或者我还没问到但您觉得重要的方面？",
                "follow_ups": [],
                "target_persona": "团队管理者",
                "dimension": "open_feedback",
            },
        ],
        "closing_script": "非常感谢您的宝贵时间！您的反馈对我们的竞品分析非常有价值。如果后续有需要澄清的地方，我们可能会通过邮件与您联系。再次感谢！",
        "estimated_duration_min": 30,
        "notes": "访谈时注意根据受访者角色调整问题侧重：管理者多问协作与管理功能，个人用户多问体验与效率。如受访者提到竞品，自然跟进询问对比体验。",
    })


async def call_mock_llm(
    messages: list[dict[str, str]],
    agent_name: str = "",
    task_id: str = "",
) -> LLMResponse:
    """Return preset LLM response for the given agent.

    Detects agent from system prompt content.
    """
    start = time.monotonic()

    # Detect agent from system message
    # IMPORTANT: "competitive analysis" appears in most prompts — avoid it.
    # Use role-specific keywords that uniquely identify each agent.
    system_msg = messages[0].get("content", "") if messages else ""
    sm = system_msg.lower()
    if "intelligence collector" in sm or ("collector" in sm and "intelligence" in sm):
        content = _collector_response()
    elif "user research operations" in sm:
        content = _fieldwork_response()
    elif "survey design expert" in sm:
        content = _survey_response()
    elif "user research expert" in sm and "interview" in sm:
        content = _interview_response()
    elif "competitive analysis expert" in sm:
        content = _analyst_response()
    elif "report writer" in sm:
        content = _writer_response()
    elif "quality assurance reviewer" in sm:
        content = _qa_response(task_id)
    else:
        # Fallback: try to detect from user message
        user_msg = messages[-1].get("content", "") if messages else ""
        um = user_msg.lower()
        if "collect information" in um or "gather information" in um:
            content = _collector_response()
        elif "design a survey" in um or "design a questionnaire" in um:
            content = _survey_response()
        elif "interview guide" in um or "semi-structured interview" in um:
            content = _interview_response()
        elif "fieldwork" in um or "simulate" in um:
            content = _fieldwork_response()
        elif "analyz" in um and "source" in um:
            content = _analyst_response()
        elif "write" in um and "report" in um:
            content = _writer_response()
        elif "review" in um or ("quality" in um and "report" in um):
            content = _qa_response(task_id)
        else:
            content = json.dumps({"error": f"Unknown agent in mock mode. system_msg: {sm[:100]}"})

    # Simulate some processing time
    await asyncio.sleep(0.1)

    duration = time.monotonic() - start
    return LLMResponse(
        content=content,
        input_tokens=len(system_msg) // 4,
        output_tokens=len(content) // 4,
        model="mock-llm",
        duration=round(duration, 3),
    )
