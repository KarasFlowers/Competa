"""Seed demo data into the Competa database.

Run: uv run python scripts/seed_demo.py

Creates a complete demo task with sources, report, traces, metrics,
and ratchet constraints — ready for frontend viewing.
"""

import asyncio
import sys
from pathlib import Path

# Ensure backend is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import async_session, create_tables
from app.models.database import (
    ConstraintModel,
    MetricsModel,
    ReportModel,
    SourceModel,
    TaskModel,
    TraceModel,
)

DEMO_TASK_ID = "demo_notion_vs_obsidian_001"


async def seed() -> None:
    await create_tables()

    async with async_session() as session:
        # Check if demo data already exists
        existing = await session.get(TaskModel, DEMO_TASK_ID)
        if existing:
            print(f"Demo task {DEMO_TASK_ID} already exists, skipping.")
            return

        # 1. Task
        task = TaskModel(
            id=DEMO_TASK_ID,
            industry="Productivity & Knowledge Management",
            target_product="Notion",
            competitors=["Obsidian", "Roam Research"],
            status="completed",
        )
        session.add(task)

        # 2. Sources (6)
        sources = [
            SourceModel(
                id="src_1",
                task_id=DEMO_TASK_ID,
                type="url",
                url="https://www.notion.so/pricing",
                title="Notion Pricing Page",
                content_snippet="Notion offers Free, Plus ($8/mo), Business ($15/mo), and Enterprise plans. Free tier includes 1 workspace, limited blocks.",
            ),
            SourceModel(
                id="src_2",
                task_id=DEMO_TASK_ID,
                type="url",
                url="https://obsidian.md/pricing",
                title="Obsidian Pricing Page",
                content_snippet="Obsidian Personal is free. Sync add-on $4/mo, Publish add-on $8/mo. Commercial license $50/user/year.",
            ),
            SourceModel(
                id="src_3",
                task_id=DEMO_TASK_ID,
                type="document",
                url=None,
                title="Product Comparison Whitepaper 2024",
                content_snippet="Notion excels in all-in-one workspace flexibility. Obsidian focuses on local-first markdown knowledge graphs. Roam Research targets bidirectional linking researchers.",
            ),
            SourceModel(
                id="src_4",
                task_id=DEMO_TASK_ID,
                type="interview",
                url=None,
                title="Interview: Product Manager at Tech Startup",
                content_snippet="We chose Notion for team collaboration but power users prefer Obsidian for personal knowledge management due to speed and plugin ecosystem.",
            ),
            SourceModel(
                id="src_5",
                task_id=DEMO_TASK_ID,
                type="interview",
                url=None,
                title="Interview: Academic Researcher",
                content_snippet="Roam Research's bidirectional links are unmatched for literature review, but the learning curve is steep and performance degrades with large graphs.",
            ),
            SourceModel(
                id="src_6",
                task_id=DEMO_TASK_ID,
                type="survey",
                url=None,
                title="User Satisfaction Survey Q1 2024",
                content_snippet="Notion: 4.2/5 ease of use, 3.8/5 performance. Obsidian: 3.5/5 ease of use, 4.7/5 performance. Roam: 3.0/5 ease of use, 3.5/5 performance.",
            ),
        ]
        for s in sources:
            session.add(s)

        # 3. Report
        report = ReportModel(
            task_id=DEMO_TASK_ID,
            title="Competitive Analysis: Notion vs Obsidian vs Roam Research",
            content={
                "title": "Competitive Analysis: Notion vs Obsidian vs Roam Research",
                "executive_summary": "Notion leads in team collaboration and all-in-one workspace features, while Obsidian excels in local-first personal knowledge management. Roam Research targets academic researchers with bidirectional linking but faces usability challenges.",
                "sections": [
                    {
                        "title": "Feature Comparison",
                        "content": "Notion offers the most comprehensive feature set for team collaboration with real-time editing, databases, and integrations. Obsidian focuses on local-first markdown with a rich plugin ecosystem.",
                        "claims": [
                            {"id": "claim_1", "content": "Notion supports real-time collaboration across all pricing tiers", "evidence_ids": ["src_1"], "confidence": 0.9, "category": "feature"},
                            {"id": "claim_2", "content": "Obsidian provides 1000+ community plugins for customization", "evidence_ids": ["src_2"], "confidence": 0.85, "category": "feature"},
                            {"id": "claim_3", "content": "Roam Research offers unmatched bidirectional linking for research", "evidence_ids": ["src_5"], "confidence": 0.8, "category": "feature"},
                        ],
                        "subsections": [],
                    },
                    {
                        "title": "Pricing Analysis",
                        "content": "Notion uses a freemium model with paid tiers starting at $8/month. Obsidian's core is free with paid sync and publish add-ons.",
                        "claims": [
                            {"id": "claim_4", "content": "Notion Plus plan costs $8/month per user", "evidence_ids": ["src_1"], "confidence": 0.95, "category": "pricing"},
                            {"id": "claim_5", "content": "Obsidian Sync costs $4/month with end-to-end encryption", "evidence_ids": ["src_2"], "confidence": 0.9, "category": "pricing"},
                        ],
                        "subsections": [],
                    },
                    {
                        "title": "User Personas",
                        "content": "Two primary personas emerge: Team Collaborators who prefer Notion, and Power Researchers who prefer Obsidian or Roam.",
                        "claims": [
                            {"id": "claim_6", "content": "Team collaborators rate Notion 4.2/5 for ease of use", "evidence_ids": ["src_6"], "confidence": 0.8, "category": "persona"},
                            {"id": "claim_7", "content": "Power researchers prefer Obsidian for personal knowledge management", "evidence_ids": ["src_4"], "confidence": 0.85, "category": "persona"},
                        ],
                        "subsections": [],
                    },
                    {
                        "title": "SWOT Analysis: Notion",
                        "content": "Notion's strengths in collaboration are offset by performance concerns with large workspaces.",
                        "claims": [
                            {"id": "claim_8", "content": "Notion's all-in-one workspace is a key strength for enterprise adoption", "evidence_ids": ["src_3"], "confidence": 0.85, "category": "swot"},
                            {"id": "claim_9", "content": "Performance issues in large workspaces remain a weakness", "evidence_ids": ["src_6"], "confidence": 0.75, "category": "swot"},
                        ],
                        "subsections": [],
                    },
                    {
                        "title": "Conclusions & Recommendations",
                        "content": "For team-heavy organizations, Notion remains the best choice. For individual knowledge workers prioritizing speed and privacy, Obsidian is superior.",
                        "claims": [
                            {"id": "claim_10", "content": "Notion is recommended for team collaboration scenarios", "evidence_ids": ["src_1", "src_4"], "confidence": 0.9, "category": "conclusion"},
                            {"id": "claim_11", "content": "Obsidian is recommended for privacy-conscious individual users", "evidence_ids": ["src_4", "src_6"], "confidence": 0.85, "category": "conclusion"},
                            {"id": "claim_12", "content": "Roam Research is best suited for academic researchers needing bidirectional links", "evidence_ids": ["src_5"], "confidence": 0.8, "category": "conclusion"},
                        ],
                        "subsections": [],
                    },
                ],
            },
            status="final",
        )
        session.add(report)

        # 4. Traces
        trace_events = [
            {"agent_name": "collector", "event_type": "start", "input_summary": "attempt 1/3", "prompt": "Collect competitive intelligence for Notion vs Obsidian, Roam Research", "retry_attempt": 1},
            {"agent_name": "collector", "event_type": "output", "output_summary": "validated CollectResult", "token_count": 1500, "duration": 2.3, "retry_attempt": 1},
            {"agent_name": "analyst", "event_type": "start", "input_summary": "attempt 1/3", "retry_attempt": 1},
            {"agent_name": "analyst", "event_type": "output", "output_summary": "validated AnalyzeResult", "token_count": 2200, "duration": 3.1, "retry_attempt": 1},
            {"agent_name": "writer", "event_type": "start", "input_summary": "attempt 1/3", "retry_attempt": 1},
            {"agent_name": "writer", "event_type": "output", "output_summary": "validated WriterReportOutput", "token_count": 1800, "duration": 2.8, "retry_attempt": 1},
            {"agent_name": "filter", "event_type": "output", "output_summary": "Filtered 0 claims without evidence"},
            {"agent_name": "qa", "event_type": "start", "input_summary": "attempt 1/3", "retry_attempt": 1},
            {"agent_name": "qa", "event_type": "output", "output_summary": "QA passed on first attempt", "token_count": 800, "duration": 1.2, "retry_attempt": 1},
        ]
        trace = TraceModel(
            task_id=DEMO_TASK_ID,
            agent_name="pipeline",
            events=trace_events,
            total_duration=9.4,
            total_tokens=6300,
            status="completed",
        )
        session.add(trace)

        # 5. Metrics
        metrics = MetricsModel(
            task_id=DEMO_TASK_ID,
            source_count=6,
            claim_count=12,
            evidence_coverage_rate=1.0,
            manual_correction_count=0,
        )
        session.add(metrics)

        # 6. Constraints (ratchet)
        constraints = [
            ConstraintModel(
                task_id=DEMO_TASK_ID,
                rule_id="ratchet_001",
                source_issue={"issue_type": "low_coverage", "field_path": "sources", "description": "Insufficient source coverage for Roam Research"},
                constraint_type="ratchet",
                constraint_value="CONSTRAINT: at least 2 sources mentioning each competitor product",
                applied_to="collector",
            ),
            ConstraintModel(
                task_id=DEMO_TASK_ID,
                rule_id="ratchet_002",
                source_issue={"issue_type": "missing_evidence", "field_path": "swot_analyses.items", "description": "SWOT items lacked evidence_ids"},
                constraint_type="ratchet",
                constraint_value="CONSTRAINT: every SWOT item must reference at least one source via evidence_ids",
                applied_to="analyst",
            ),
        ]
        for c in constraints:
            session.add(c)

        await session.commit()

    print(f"Demo data seeded successfully!")
    print(f"  Task ID: {DEMO_TASK_ID}")
    print(f"  View at: http://127.0.0.1:5173/tasks/{DEMO_TASK_ID}")
    print(f"  Report:  http://127.0.0.1:5173/tasks/{DEMO_TASK_ID}/report")


if __name__ == "__main__":
    asyncio.run(seed())
