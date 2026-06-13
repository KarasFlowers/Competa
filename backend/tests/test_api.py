"""Tests for the FastAPI endpoints."""

import asyncio
from datetime import datetime, timedelta

from httpx import AsyncClient

from app.models.database import (
    AnalysisModel,
    ConstraintModel,
    InterviewModel,
    MetricsModel,
    ReportModel,
    RunHistoryModel,
    SourceModel,
    SurveyModel,
    TaskModel,
    TraceModel,
)
from tests.conftest import TestSession


async def _noop_run_pipeline(
    task_id: str,
    *,
    resume: bool = False,
    state_overrides: dict | None = None,
) -> None:
    return None


class TestHealth:
    async def test_health(self, client: AsyncClient):
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestTasks:
    async def test_create_and_list(self, client: AsyncClient):
        resp = await client.post(
            "/api/tasks",
            json={
                "industry": "SaaS",
                "target_product": "ProductA",
                "target_website": "https://producta.example.com",
                "competitors": ["ProductB", "ProductC"],
                "focus_areas": ["pricing", "persona", "pricing"],
                "human_review_required": True,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["target_product"] == "ProductA"
        assert data["target_website"] == "https://producta.example.com"
        assert data["human_review_required"] is True
        assert data["focus_areas"] == ["pricing", "persona"]
        task_id = data["id"]

        resp = await client.get("/api/tasks")
        assert resp.status_code == 200
        created_task = next((task for task in resp.json() if task["id"] == task_id), None)
        ids = [t["id"] for t in resp.json()]
        assert task_id in ids
        assert created_task is not None
        assert created_task["target_website"] == "https://producta.example.com"
        assert created_task["human_review_required"] is True

    async def test_get_task(self, client: AsyncClient):
        resp = await client.post(
            "/api/tasks",
            json={"target_product": "X", "target_website": "https://x.example.com"},
        )
        task_id = resp.json()["id"]

        resp = await client.get(f"/api/tasks/{task_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == task_id
        assert resp.json()["target_website"] == "https://x.example.com"

    async def test_get_task_includes_last_curation_summary(self, client: AsyncClient):
        resp = await client.post(
            "/api/tasks",
            json={"target_product": "TaskWithCuration"},
        )
        task_id = resp.json()["id"]

        async with TestSession() as session:
            task = await session.get(TaskModel, task_id)
            task.last_curation_summary = {
                "input_count": 6,
                "kept_count": 4,
                "removed_count": 2,
                "removed_reasons": {"low_reliability": 2},
            }
            await session.commit()

        detail = await client.get(f"/api/tasks/{task_id}")
        assert detail.status_code == 200
        assert detail.json()["last_curation_summary"]["kept_count"] == 4

    async def test_get_nonexistent_task(self, client: AsyncClient):
        resp = await client.get("/api/tasks/nonexistent")
        assert resp.status_code == 404

    async def test_tasks_overview_returns_stats_and_artifacts(self, client: AsyncClient):
        resp = await client.post(
            "/api/tasks",
            json={
                "industry": "AI",
                "target_product": "WorkspaceA",
                "target_website": "https://workspacea.example.com",
                "competitors": ["Alpha", "Beta"],
                "focus_areas": ["pricing", "swot"],
                "our_product_notes": "Internal differentiation notes",
            },
        )
        task_id = resp.json()["id"]

        resp = await client.post(
            "/api/tasks",
            json={"industry": "AI", "target_product": "WorkspaceB"},
        )
        failed_task_id = resp.json()["id"]
        resp = await client.post(
            "/api/tasks",
            json={"industry": "AI", "target_product": "WorkspaceC"},
        )
        review_task_id = resp.json()["id"]

        async with TestSession() as session:
            failed_task = await session.get(TaskModel, failed_task_id)
            failed_task.status = "failed"
            review_task = await session.get(TaskModel, review_task_id)
            review_task.status = "awaiting_review"
            focus_task = await session.get(TaskModel, task_id)
            focus_task.last_curation_summary = {
                "input_count": 9,
                "kept_count": 6,
                "removed_count": 3,
                "removed_reasons": {"domain_cap": 1, "low_reliability": 2},
            }
            session.add_all([
                MetricsModel(
                    task_id=task_id,
                    source_count=6,
                    claim_count=9,
                    evidence_coverage_rate=0.88,
                    quality_score=0.82,
                    quality_breakdown={"score": 0.82},
                    manual_correction_count=1,
                ),
                ReportModel(task_id=task_id, title="Report", content={"title": "R"}),
                AnalysisModel(task_id=task_id, content={"feature_trees": []}),
                TraceModel(task_id=task_id, agent_name="pipeline", events=[]),
                SurveyModel(task_id=task_id, content={"title": "Survey"}),
                InterviewModel(task_id=task_id, content={"title": "Interview"}),
            ])
            await session.commit()

        resp = await client.get("/api/tasks/overview")
        assert resp.status_code == 200
        data = resp.json()

        assert data["stats"]["total_tasks"] >= 3
        assert data["stats"]["failed_tasks"] >= 1
        assert data["stats"]["review_tasks"] >= 1
        assert data["stats"]["reports_ready"] >= 1
        assert data["stats"]["avg_evidence_coverage"] == 0.88
        assert data["stats"]["avg_quality_score"] == 0.82

        item = next(t for t in data["items"] if t["id"] == task_id)
        assert item["target_website"] == "https://workspacea.example.com"
        assert item["our_product_notes"] == "Internal differentiation notes"
        assert item["focus_areas"] == ["pricing", "swot"]
        assert item["last_curation_summary"]["kept_count"] == 6
        assert item["metrics"]["source_count"] == 6
        assert item["metrics"]["quality_score"] == 0.82
        assert item["metrics"]["quality_breakdown"] == {"score": 0.82}
        assert item["artifacts"] == {
            "report": True,
            "analysis": True,
            "traces": True,
            "survey": True,
            "interview": True,
        }


class TestReportsAndSources:
    async def test_report_not_found(self, client: AsyncClient):
        resp = await client.get("/api/tasks/fake/report")
        assert resp.status_code == 404

    async def test_report_returns_latest(self, client: AsyncClient):
        resp = await client.post("/api/tasks", json={"target_product": "LatestReport"})
        task_id = resp.json()["id"]
        now = datetime.utcnow()

        async with TestSession() as session:
            session.add_all([
                ReportModel(
                    task_id=task_id,
                    title="Older Report",
                    content={"title": "older"},
                    status="draft",
                    created_at=now - timedelta(minutes=5),
                ),
                ReportModel(
                    task_id=task_id,
                    title="Latest Report",
                    content={"title": "latest"},
                    status="final",
                    created_at=now,
                ),
            ])
            await session.commit()

        resp = await client.get(f"/api/tasks/{task_id}/report")
        assert resp.status_code == 200
        assert resp.json()["title"] == "Latest Report"

    async def test_sources_empty(self, client: AsyncClient):
        resp = await client.post("/api/tasks", json={"target_product": "Y"})
        task_id = resp.json()["id"]
        resp = await client.get(f"/api/tasks/{task_id}/sources")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_sources_return_curation_fields_and_sort_included_first(self, client: AsyncClient):
        resp = await client.post("/api/tasks", json={"target_product": "CuratedSources"})
        task_id = resp.json()["id"]
        now = datetime.utcnow()

        async with TestSession() as session:
            session.add_all([
                SourceModel(
                    task_id=task_id,
                    id="src-excluded",
                    title="Excluded",
                    content_snippet="excluded snippet",
                    reliability_score=0.99,
                    included_in_analysis=False,
                    curation_reason="domain_cap",
                    curation_tags=["high_confidence"],
                    curated_excerpt="Excluded excerpt",
                    fetched_at=now - timedelta(minutes=3),
                ),
                SourceModel(
                    task_id=task_id,
                    id="src-included-high",
                    title="Included High",
                    content_snippet="included high snippet",
                    reliability_score=0.91,
                    included_in_analysis=True,
                    curation_reason="selected",
                    curation_tags=["high_confidence"],
                    curated_excerpt="Included high excerpt",
                    fetched_at=now - timedelta(minutes=2),
                ),
                SourceModel(
                    task_id=task_id,
                    id="src-included-mid",
                    title="Included Mid",
                    content_snippet="included mid snippet",
                    reliability_score=0.72,
                    included_in_analysis=True,
                    curation_reason="selected",
                    curation_tags=["medium_confidence"],
                    curated_excerpt="Included mid excerpt",
                    fetched_at=now - timedelta(minutes=1),
                ),
            ])
            await session.commit()

        result = await client.get(f"/api/tasks/{task_id}/sources")
        assert result.status_code == 200
        payload = result.json()
        assert [item["id"] for item in payload] == [
            "src-included-high",
            "src-included-mid",
            "src-excluded",
        ]
        assert payload[0]["included_in_analysis"] is True
        assert payload[0]["curation_reason"] == "selected"
        assert payload[0]["curated_excerpt"] == "Included high excerpt"
        assert payload[2]["included_in_analysis"] is False
        assert payload[2]["curation_reason"] == "domain_cap"

    async def test_markdown_export_includes_curation_sections(self, client: AsyncClient):
        resp = await client.post("/api/tasks", json={"target_product": "ExportMarkdown"})
        task_id = resp.json()["id"]

        async with TestSession() as session:
            session.add(ReportModel(
                task_id=task_id,
                title="Export Report",
                content={
                    "title": "Export Report",
                    "executive_summary": "Summary text",
                    "sections": [
                        {
                            "title": "Overview",
                            "content": "Overview content",
                            "claims": [
                                {"content": "Claim 1", "evidence_ids": ["src-included"]},
                            ],
                        },
                    ],
                },
                status="final",
            ))
            session.add_all([
                SourceModel(
                    task_id=task_id,
                    id="src-included",
                    title="Included source",
                    type="web",
                    url="https://example.com/included",
                    content_snippet="Included snippet",
                    reliability_score=0.86,
                    included_in_analysis=True,
                    curation_reason="selected",
                    curation_tags=["pricing", "first_party"],
                    curated_excerpt="Included excerpt",
                ),
                SourceModel(
                    task_id=task_id,
                    id="src-excluded",
                    title="Excluded source",
                    type="web",
                    url="https://example.com/excluded",
                    content_snippet="Excluded snippet",
                    reliability_score=0.42,
                    included_in_analysis=False,
                    curation_reason="domain_cap",
                    curation_tags=["redundant"],
                    curated_excerpt="Excluded excerpt",
                ),
            ])
            await session.commit()

        export_resp = await client.get(f"/api/tasks/{task_id}/export?format=markdown")
        assert export_resp.status_code == 200
        assert export_resp.headers["content-type"].startswith("text/markdown")
        assert export_resp.headers["content-disposition"] == f'attachment; filename="report_{task_id}.md"'
        assert "## Sources Used in Analysis" in export_resp.text
        assert "## Excluded or Deprioritized Sources" in export_resp.text
        assert "Curation: Included in analysis" in export_resp.text
        assert "Curation: Removed due to domain diversity cap" in export_resp.text
        assert "Excerpt: Included excerpt" in export_resp.text
        assert "Excerpt: Excluded excerpt" in export_resp.text

    async def test_docx_export_returns_downloadable_file(self, client: AsyncClient):
        resp = await client.post("/api/tasks", json={"target_product": "ExportDocx"})
        task_id = resp.json()["id"]

        async with TestSession() as session:
            session.add(ReportModel(
                task_id=task_id,
                title="Docx Report",
                content={"title": "Docx Report", "sections": [{"title": "Overview", "content": "Body"}]},
                status="final",
            ))
            await session.commit()

        export_resp = await client.get(f"/api/tasks/{task_id}/export?format=docx")
        assert export_resp.status_code == 200
        assert export_resp.headers["content-type"] == (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        assert export_resp.headers["content-disposition"] == f'attachment; filename="report_{task_id}.docx"'
        assert export_resp.content.startswith(b"PK")

    async def test_metrics_returns_latest(self, client: AsyncClient):
        resp = await client.post("/api/tasks", json={"target_product": "LatestMetrics"})
        task_id = resp.json()["id"]
        now = datetime.utcnow()

        async with TestSession() as session:
            session.add_all([
                MetricsModel(
                    task_id=task_id,
                    source_count=1,
                    claim_count=1,
                    evidence_coverage_rate=0.5,
                    quality_score=0.4,
                    manual_correction_count=0,
                    calculated_at=now - timedelta(minutes=5),
                ),
                MetricsModel(
                    task_id=task_id,
                    source_count=4,
                    claim_count=6,
                    evidence_coverage_rate=0.9,
                    quality_score=0.86,
                    quality_breakdown={"score": 0.86},
                    manual_correction_count=0,
                    calculated_at=now,
                ),
            ])
            await session.commit()

        resp = await client.get(f"/api/tasks/{task_id}/metrics")
        assert resp.status_code == 200
        assert resp.json()["source_count"] == 4
        assert resp.json()["quality_score"] == 0.86
        assert resp.json()["quality_breakdown"] == {"score": 0.86}


class TestTraces:
    async def test_traces_empty(self, client: AsyncClient):
        resp = await client.post("/api/tasks", json={"target_product": "Z"})
        task_id = resp.json()["id"]
        resp = await client.get(f"/api/tasks/{task_id}/traces")
        assert resp.status_code == 200
        assert resp.json() == []


class TestRunAndStatus:
    async def test_run_nonexistent_task(self, client: AsyncClient):
        resp = await client.post("/api/tasks/nonexistent/run")
        assert resp.status_code == 404

    async def test_run_returns_202(self, client: AsyncClient, monkeypatch):
        monkeypatch.setattr("app.api.tasks.run_pipeline", _noop_run_pipeline)
        resp = await client.post("/api/tasks", json={"target_product": "TestProd"})
        task_id = resp.json()["id"]

        resp = await client.post(f"/api/tasks/{task_id}/run")
        assert resp.status_code == 202
        assert resp.json()["task_id"] == task_id

    async def test_second_run_conflicts_after_atomic_claim(self, client: AsyncClient, monkeypatch):
        monkeypatch.setattr("app.api.tasks.run_pipeline", _noop_run_pipeline)
        resp = await client.post("/api/tasks", json={"target_product": "NoDoubleRun"})
        task_id = resp.json()["id"]

        first = await client.post(f"/api/tasks/{task_id}/run")
        second = await client.post(f"/api/tasks/{task_id}/run")

        assert first.status_code == 202
        assert second.status_code == 409
        assert "collecting" in second.json()["detail"]

    async def test_run_conflict_if_not_pending(self, client: AsyncClient):
        """Tasks already running should reject /run."""
        resp = await client.post("/api/tasks", json={"target_product": "TestProd2"})
        task_id = resp.json()["id"]

        async with TestSession() as session:
            task = await session.get(TaskModel, task_id)
            task.status = "collecting"
            await session.commit()

        resp = await client.post(f"/api/tasks/{task_id}/run")
        assert resp.status_code == 409

    async def test_failed_task_run_resumes_checkpoint_without_purging_context(self, client: AsyncClient, monkeypatch):
        captured: dict[str, bool] = {}

        async def _capture_run_pipeline(task_id: str, *, resume: bool = False) -> None:
            captured["resume"] = resume

        monkeypatch.setattr("app.api.tasks.run_pipeline", _capture_run_pipeline)
        resp = await client.post("/api/tasks", json={"target_product": "ResumeFailed"})
        task_id = resp.json()["id"]

        async with TestSession() as session:
            task = await session.get(TaskModel, task_id)
            task.status = "failed"
            task.last_qa_feedback = {"passed": False}
            session.add_all([
                SourceModel(task_id=task_id, title="Keep Source", content_snippet="keep"),
                ConstraintModel(task_id=task_id, constraint_type="human", constraint_value="keep-constraint"),
            ])
            await session.commit()

        resp = await client.post(f"/api/tasks/{task_id}/run")
        await asyncio.sleep(0)
        assert resp.status_code == 202
        assert captured["resume"] is True

        async with TestSession() as session:
            source = await session.execute(SourceModel.__table__.select().where(SourceModel.task_id == task_id))
            constraint = await session.execute(ConstraintModel.__table__.select().where(ConstraintModel.task_id == task_id))
            task = await session.get(TaskModel, task_id)

        assert task.status == "collecting"
        assert source.first() is not None
        assert constraint.first() is not None

    async def test_continue_after_review_adds_writer_constraint_and_resumes(self, client: AsyncClient, monkeypatch):
        captured: dict[str, object] = {}

        async def _capture_run_pipeline(
            task_id: str,
            *,
            resume: bool = False,
            state_overrides: dict | None = None,
        ) -> None:
            captured["resume"] = resume
            captured["state_overrides"] = state_overrides

        monkeypatch.setattr("app.api.tasks.run_pipeline", _capture_run_pipeline)
        resp = await client.post(
            "/api/tasks",
            json={"target_product": "ReviewTask", "human_review_required": True},
        )
        task_id = resp.json()["id"]

        async with TestSession() as session:
            task = await session.get(TaskModel, task_id)
            task.status = "awaiting_review"
            await session.commit()

        resp = await client.post(
            f"/api/tasks/{task_id}/continue",
            json={"instruction": "强调企业治理能力"},
        )
        await asyncio.sleep(0)
        assert resp.status_code == 202
        assert captured["resume"] is True
        assert "强调企业治理能力" in " ".join(captured["state_overrides"]["constraints"])

        async with TestSession() as session:
            task = await session.get(TaskModel, task_id)
            constraints = (
                await session.execute(
                    ConstraintModel.__table__.select().where(ConstraintModel.task_id == task_id)
                )
            ).fetchall()

        assert task.status == "writing"
        assert task.manual_correction_count == 1
        assert any(row.constraint_value.startswith("CONSTRAINT: human review") for row in constraints)

    async def test_second_continue_after_review_conflicts_after_atomic_claim(self, client: AsyncClient, monkeypatch):
        monkeypatch.setattr("app.api.tasks.run_pipeline", _noop_run_pipeline)
        resp = await client.post(
            "/api/tasks",
            json={"target_product": "ReviewNoDouble", "human_review_required": True},
        )
        task_id = resp.json()["id"]

        async with TestSession() as session:
            task = await session.get(TaskModel, task_id)
            task.status = "awaiting_review"
            await session.commit()

        first = await client.post(f"/api/tasks/{task_id}/continue", json={"instruction": "first"})
        second = await client.post(f"/api/tasks/{task_id}/continue", json={"instruction": "second"})

        assert first.status_code == 202
        assert second.status_code == 409
        assert "writing" in second.json()["detail"]

    async def test_background_exception_marks_task_failed(self, client: AsyncClient, monkeypatch):
        async def _boom_run_pipeline(task_id: str, *, resume: bool = False) -> None:
            raise RuntimeError("runner exploded")

        monkeypatch.setattr("app.api.tasks.run_pipeline", _boom_run_pipeline)
        monkeypatch.setattr("app.api.tasks.async_session", TestSession)
        resp = await client.post("/api/tasks", json={"target_product": "FailingBackground"})
        task_id = resp.json()["id"]

        run = await client.post(f"/api/tasks/{task_id}/run")
        for _ in range(10):
            await asyncio.sleep(0)

        assert run.status_code == 202
        async with TestSession() as session:
            task = await session.get(TaskModel, task_id)

        assert task.status == "failed"
        assert task.last_qa_feedback["issues"][0]["issue_type"] == "background_task_error"

    async def test_completed_task_can_run_again_and_purges_old_artifacts(self, client: AsyncClient, monkeypatch):
        monkeypatch.setattr("app.api.tasks.run_pipeline", _noop_run_pipeline)
        resp = await client.post("/api/tasks", json={"target_product": "RerunTarget"})
        task_id = resp.json()["id"]

        async with TestSession() as session:
            task = await session.get(TaskModel, task_id)
            task.status = "completed"
            task.last_qa_feedback = {"passed": True}
            task.last_handoff = {"target_agent": "writer"}
            task.last_curation_summary = {"kept_count": 3}
            session.add_all([
                SourceModel(task_id=task_id, title="Old Source", content_snippet="old"),
                ReportModel(task_id=task_id, title="Old Report", content={"title": "old"}),
                TraceModel(task_id=task_id, agent_name="pipeline", events=[{"event": "old"}]),
                MetricsModel(task_id=task_id, source_count=1, claim_count=1, evidence_coverage_rate=1.0),
                ConstraintModel(task_id=task_id, constraint_value="old"),
                AnalysisModel(task_id=task_id, content={"feature_trees": []}),
                SurveyModel(task_id=task_id, content={"title": "Survey"}),
                InterviewModel(task_id=task_id, content={"title": "Interview"}),
            ])
            await session.commit()

        rerun = await client.post(f"/api/tasks/{task_id}/run")
        assert rerun.status_code == 202

        async with TestSession() as session:
            task = await session.get(TaskModel, task_id)
            assert task.status == "collecting"
            assert task.last_qa_feedback == {}
            assert task.last_handoff == {}
            assert task.last_curation_summary == {}

            for model in (
                SourceModel,
                ReportModel,
                TraceModel,
                MetricsModel,
                ConstraintModel,
                AnalysisModel,
                SurveyModel,
                InterviewModel,
            ):
                result = await session.execute(model.__table__.select().where(model.task_id == task_id))
                assert result.first() is None

    async def test_rerun_preserves_sources_and_constraints_but_clears_artifacts(self, client: AsyncClient, monkeypatch):
        monkeypatch.setattr("app.api.tasks.run_pipeline", _noop_run_pipeline)
        resp = await client.post("/api/tasks", json={"target_product": "PreserveSources"})
        task_id = resp.json()["id"]

        async with TestSession() as session:
            task = await session.get(TaskModel, task_id)
            task.status = "completed"
            task.last_qa_feedback = {"passed": False}
            task.last_handoff = {"target_agent": "analyst"}
            task.last_curation_summary = {"kept_count": 2}
            session.add_all([
                SourceModel(task_id=task_id, title="Keep Source", content_snippet="keep"),
                ConstraintModel(task_id=task_id, constraint_type="human", constraint_value="keep-constraint"),
                ReportModel(task_id=task_id, title="Old Report", content={"title": "old"}),
                TraceModel(task_id=task_id, agent_name="pipeline", events=[{"event": "old"}]),
                MetricsModel(task_id=task_id, source_count=1, claim_count=1, evidence_coverage_rate=1.0),
                AnalysisModel(task_id=task_id, content={"feature_trees": []}),
                SurveyModel(task_id=task_id, content={"title": "Survey"}),
                InterviewModel(task_id=task_id, content={"title": "Interview"}),
            ])
            await session.commit()

        rerun = await client.post(f"/api/tasks/{task_id}/rerun")
        assert rerun.status_code == 202

        async with TestSession() as session:
            task = await session.get(TaskModel, task_id)
            assert task.status == "collecting"
            assert task.last_qa_feedback == {}
            assert task.last_handoff == {}
            assert task.last_curation_summary == {}

            sources = await session.execute(SourceModel.__table__.select().where(SourceModel.task_id == task_id))
            constraints = await session.execute(ConstraintModel.__table__.select().where(ConstraintModel.task_id == task_id))
            assert sources.first() is not None
            assert constraints.first() is not None

            for model in (ReportModel, TraceModel, MetricsModel, AnalysisModel, SurveyModel, InterviewModel):
                result = await session.execute(model.__table__.select().where(model.task_id == task_id))
                assert result.first() is None

    async def test_second_rerun_conflicts_after_atomic_claim(self, client: AsyncClient, monkeypatch):
        monkeypatch.setattr("app.api.tasks.run_pipeline", _noop_run_pipeline)
        resp = await client.post("/api/tasks", json={"target_product": "NoDoubleRerun"})
        task_id = resp.json()["id"]

        async with TestSession() as session:
            task = await session.get(TaskModel, task_id)
            task.status = "completed"
            await session.commit()

        first = await client.post(f"/api/tasks/{task_id}/rerun")
        second = await client.post(f"/api/tasks/{task_id}/rerun")

        assert first.status_code == 202
        assert second.status_code == 409
        assert "collecting" in second.json()["detail"]

    async def test_status_endpoint(self, client: AsyncClient):
        resp = await client.post("/api/tasks", json={"target_product": "StatusTest"})
        task_id = resp.json()["id"]

        resp = await client.get(f"/api/tasks/{task_id}/status")
        assert resp.status_code == 200
        assert resp.json()["status"] == "pending"
        assert resp.json()["id"] == task_id


class TestCORS:
    async def test_cors_no_wildcard_with_credentials(self, client: AsyncClient):
        """CORS should not return Access-Control-Allow-Credentials with wildcard origin."""
        resp = await client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        # Should not have Access-Control-Allow-Credentials: true
        assert resp.headers.get("access-control-allow-credentials") is None


class TestCorrections:
    async def test_edit_claim_nested_subsection(self, client: AsyncClient):
        """edit_claim should find claims in nested subsections."""
        resp = await client.post("/api/tasks", json={"target_product": "NestedClaim"})
        task_id = resp.json()["id"]

        report_content = {
            "sections": [
                {
                    "title": "Overview",
                    "claims": [{"id": "c1", "content": "top claim"}],
                    "subsections": [
                        {
                            "title": "Details",
                            "claims": [{"id": "c2", "content": "nested claim"}],
                            "subsections": [],
                        },
                    ],
                },
            ]
        }

        async with TestSession() as session:
            session.add(ReportModel(
                task_id=task_id,
                title="Test Report",
                content=report_content,
                status="final",
            ))
            await session.commit()

        resp = await client.post(
            f"/api/tasks/{task_id}/corrections",
            json={
                "correction_type": "edit_claim",
                "data": {"claim_id": "c2", "content": "updated nested claim"},
            },
        )
        assert resp.status_code == 200

        # Verify the nested claim was updated
        async with TestSession() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(ReportModel).where(ReportModel.task_id == task_id)
            )
            report = result.scalars().first()
            # Find the nested claim
            for section in report.content["sections"]:
                for sub in section.get("subsections", []):
                    for claim in sub.get("claims", []):
                        if claim["id"] == "c2":
                            assert claim["content"] == "updated nested claim"

    async def test_edit_claim_top_level(self, client: AsyncClient):
        """edit_claim should still work for top-level claims."""
        resp = await client.post("/api/tasks", json={"target_product": "TopClaim"})
        task_id = resp.json()["id"]

        report_content = {
            "sections": [
                {
                    "title": "Overview",
                    "claims": [{"id": "c1", "content": "original"}],
                    "subsections": [],
                },
            ]
        }

        async with TestSession() as session:
            session.add(ReportModel(
                task_id=task_id,
                title="Test Report",
                content=report_content,
                status="final",
            ))
            await session.commit()

        resp = await client.post(
            f"/api/tasks/{task_id}/corrections",
            json={
                "correction_type": "edit_claim",
                "data": {"claim_id": "c1", "content": "updated"},
            },
        )
        assert resp.status_code == 200

    async def test_human_corrections_increment_task_counter(self, client: AsyncClient):
        resp = await client.post("/api/tasks", json={"target_product": "CorrectionsCounter"})
        task_id = resp.json()["id"]

        async with TestSession() as session:
            session.add(ReportModel(
                task_id=task_id,
                title="Test Report",
                content={"sections": [{"title": "Overview", "claims": [{"id": "c1", "content": "original"}]}]},
                status="final",
            ))
            await session.commit()

        add_source = await client.post(
            f"/api/tasks/{task_id}/corrections",
            json={
                "correction_type": "add_source",
                "data": {"title": "Extra Source", "content_snippet": "details"},
            },
        )
        assert add_source.status_code == 200

        edit_claim = await client.post(
            f"/api/tasks/{task_id}/corrections",
            json={
                "correction_type": "edit_claim",
                "data": {"claim_id": "c1", "content": "updated"},
            },
        )
        assert edit_claim.status_code == 200

        task_resp = await client.get(f"/api/tasks/{task_id}")
        assert task_resp.status_code == 200
        assert task_resp.json()["manual_correction_count"] == 2

    async def test_constraints_endpoint_returns_latest_constraints(self, client: AsyncClient):
        resp = await client.post("/api/tasks", json={"target_product": "ConstraintQuery"})
        task_id = resp.json()["id"]

        async with TestSession() as session:
            session.add_all([
                ConstraintModel(
                    task_id=task_id,
                    constraint_type="ratchet",
                    constraint_value="CONSTRAINT: add evidence",
                    applied_to="writer",
                ),
                ConstraintModel(
                    task_id=task_id,
                    constraint_type="human",
                    constraint_value="CONSTRAINT: expand pricing comparison",
                    applied_to="analyst",
                ),
            ])
            await session.commit()

        result = await client.get(f"/api/tasks/{task_id}/constraints")
        assert result.status_code == 200
        values = [item["constraint_value"] for item in result.json()]
        assert "CONSTRAINT: add evidence" in values
        assert "CONSTRAINT: expand pricing comparison" in values

    async def test_run_history_endpoints_return_runs_and_comparison(self, client: AsyncClient):
        resp = await client.post("/api/tasks", json={"target_product": "RunHistoryTask"})
        task_id = resp.json()["id"]

        async with TestSession() as session:
            session.add_all([
                RunHistoryModel(
                    task_id=task_id,
                    run_index=1,
                    status="completed",
                    source_count=4,
                    claim_count=8,
                    evidence_coverage_rate=0.62,
                    quality_score=0.58,
                    retry_count=1,
                    manual_correction_count=2,
                    qa_feedback={"passed": False},
                    curation_summary={"input_count": 6, "kept_count": 4, "removed_count": 2},
                ),
                RunHistoryModel(
                    task_id=task_id,
                    run_index=2,
                    status="completed",
                    source_count=7,
                    claim_count=10,
                    evidence_coverage_rate=0.91,
                    quality_score=0.84,
                    retry_count=0,
                    manual_correction_count=2,
                    qa_feedback={"passed": True},
                    curation_summary={"input_count": 9, "kept_count": 7, "removed_count": 2},
                ),
            ])
            await session.commit()

        runs = await client.get(f"/api/tasks/{task_id}/runs")
        assert runs.status_code == 200
        assert [item["run_index"] for item in runs.json()] == [2, 1]
        assert runs.json()[0]["curation_summary"]["kept_count"] == 7
        assert runs.json()[0]["quality_score"] == 0.84

        compare = await client.get(f"/api/tasks/{task_id}/runs/latest/compare")
        assert compare.status_code == 200
        payload = compare.json()
        assert payload["current"]["run_index"] == 2
        assert payload["previous"]["run_index"] == 1
        assert payload["current"]["curation_summary"]["input_count"] == 9
        assert payload["delta"] == {
            "source_count_delta": 3,
            "claim_count_delta": 2,
            "evidence_coverage_delta": 0.29,
            "quality_score_delta": 0.26,
            "retry_count_delta": -1,
            "manual_correction_delta": 0,
        }


class TestDagEndpoint:
    async def test_get_dag_structure(self, client: AsyncClient):
        """DAG endpoint should return nodes and edges with correct structure."""
        resp = await client.post(
            "/api/tasks",
            json={"target_product": "DagTest", "competitors": ["CompA"]},
        )
        task_id = resp.json()["id"]

        resp = await client.get(f"/api/tasks/{task_id}/dag")
        assert resp.status_code == 200
        data = resp.json()

        # Check nodes
        assert "nodes" in data
        assert "edges" in data
        node_ids = {n["id"] for n in data["nodes"]}
        assert node_ids == {
            "collector", "survey", "interview", "fieldwork", "curator", "analyst",
            "writer", "screenshot", "filter", "qa",
        }

        # Check node fields
        for n in data["nodes"]:
            assert "id" in n
            assert "label" in n
            assert "type" in n
            assert "status" in n

        # Check edges include forward flow + retry edges
        edge_pairs = {(e["source"], e["target"]) for e in data["edges"]}
        assert ("collector", "survey") in edge_pairs
        assert ("interview", "fieldwork") in edge_pairs
        assert ("fieldwork", "curator") in edge_pairs
        assert ("curator", "analyst") in edge_pairs
        assert ("analyst", "writer") in edge_pairs
        assert ("qa", "collector") in edge_pairs
        assert ("qa", "analyst") in edge_pairs
        assert ("qa", "writer") in edge_pairs

        # Pending task → all nodes pending
        statuses = {n["id"]: n["status"] for n in data["nodes"]}
        assert all(s == "pending" for s in statuses.values())

    async def test_get_dag_not_found(self, client: AsyncClient):
        resp = await client.get("/api/tasks/nonexistent/dag")
        assert resp.status_code == 404
