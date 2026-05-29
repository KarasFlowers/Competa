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
                    {"content": "Notion supports real-time collaboration across all pricing tiers", "evidence_ids": ["src_1"], "confidence": 0.9, "category": "feature"},
                    {"content": "Obsidian provides 1000+ community plugins for customization", "evidence_ids": ["src_2"], "confidence": 0.85, "category": "feature"},
                ],
                "subsections": [],
            },
            {
                "title": "Pricing Analysis",
                "content": "Notion uses a freemium model with paid tiers starting at $8/month. Obsidian's core is free with paid sync and publish add-ons.",
                "claims": [
                    {"content": "Notion Plus plan costs $8/month per user", "evidence_ids": ["src_1"], "confidence": 0.95, "category": "pricing"},
                    {"content": "Obsidian Sync costs $4/month with end-to-end encryption", "evidence_ids": ["src_2"], "confidence": 0.9, "category": "pricing"},
                ],
                "subsections": [],
            },
            {
                "title": "User Personas",
                "content": "Two primary personas emerge: Team Collaborators who prefer Notion, and Power Researchers who prefer Obsidian or Roam.",
                "claims": [
                    {"content": "Team collaborators rate Notion 4.2/5 for ease of use", "evidence_ids": ["src_4"], "confidence": 0.8, "category": "persona"},
                    {"content": "Power researchers prefer Obsidian for personal knowledge management", "evidence_ids": ["src_3"], "confidence": 0.85, "category": "persona"},
                ],
                "subsections": [],
            },
            {
                "title": "SWOT Analysis: Notion",
                "content": "Notion's strengths in collaboration are offset by performance concerns with large workspaces.",
                "claims": [
                    {"content": "Notion's all-in-one workspace is a key strength for enterprise adoption", "evidence_ids": ["src_2"], "confidence": 0.85, "category": "swot"},
                    {"content": "Performance issues in large workspaces remain a weakness", "evidence_ids": ["src_4"], "confidence": 0.75, "category": "swot"},
                ],
                "subsections": [],
            },
            {
                "title": "Conclusions & Recommendations",
                "content": "For team-heavy organizations, Notion remains the best choice. For individual knowledge workers prioritizing speed and privacy, Obsidian is superior.",
                "claims": [
                    {"content": "Notion is recommended for team collaboration scenarios", "evidence_ids": ["src_1", "src_3"], "confidence": 0.9, "category": "conclusion"},
                    {"content": "Obsidian is recommended for privacy-conscious individual users", "evidence_ids": ["src_3", "src_4"], "confidence": 0.85, "category": "conclusion"},
                ],
                "subsections": [],
            },
        ],
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
    system_msg = messages[0].get("content", "") if messages else ""
    if "collector" in system_msg.lower() or "intelligence collector" in system_msg.lower():
        content = _collector_response()
    elif "analysis expert" in system_msg.lower() or "competitive analysis" in system_msg.lower():
        content = _analyst_response()
    elif "report writer" in system_msg.lower() or "professional competitive" in system_msg.lower():
        content = _writer_response()
    elif "quality assurance" in system_msg.lower() or "qa reviewer" in system_msg.lower():
        content = _qa_response(task_id)
    else:
        # Fallback: try to detect from user message
        user_msg = messages[-1].get("content", "") if messages else ""
        if "collect" in user_msg.lower():
            content = _collector_response()
        elif "analyz" in user_msg.lower():
            content = _analyst_response()
        elif "write" in user_msg.lower() or "report" in user_msg.lower():
            content = _writer_response()
        elif "review" in user_msg.lower() or "quality" in user_msg.lower():
            content = _qa_response(task_id)
        else:
            content = json.dumps({"error": "Unknown agent in mock mode"})

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
