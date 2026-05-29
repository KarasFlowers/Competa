"""Tests for the FastAPI endpoints."""

from datetime import datetime, timedelta

from httpx import AsyncClient

from app.models.database import ConstraintModel, MetricsModel, ReportModel, SourceModel, TaskModel, TraceModel
from tests.conftest import TestSession


async def _noop_run_pipeline(task_id: str) -> None:
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
                "competitors": ["ProductB", "ProductC"],
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["target_product"] == "ProductA"
        task_id = data["id"]

        resp = await client.get("/api/tasks")
        assert resp.status_code == 200
        ids = [t["id"] for t in resp.json()]
        assert task_id in ids

    async def test_get_task(self, client: AsyncClient):
        resp = await client.post(
            "/api/tasks",
            json={"target_product": "X"},
        )
        task_id = resp.json()["id"]

        resp = await client.get(f"/api/tasks/{task_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == task_id

    async def test_get_nonexistent_task(self, client: AsyncClient):
        resp = await client.get("/api/tasks/nonexistent")
        assert resp.status_code == 404


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
                    manual_correction_count=0,
                    calculated_at=now - timedelta(minutes=5),
                ),
                MetricsModel(
                    task_id=task_id,
                    source_count=4,
                    claim_count=6,
                    evidence_coverage_rate=0.9,
                    manual_correction_count=0,
                    calculated_at=now,
                ),
            ])
            await session.commit()

        resp = await client.get(f"/api/tasks/{task_id}/metrics")
        assert resp.status_code == 200
        assert resp.json()["source_count"] == 4


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

    async def test_completed_task_can_rerun_and_purges_old_artifacts(self, client: AsyncClient, monkeypatch):
        monkeypatch.setattr("app.api.tasks.run_pipeline", _noop_run_pipeline)
        resp = await client.post("/api/tasks", json={"target_product": "RerunTarget"})
        task_id = resp.json()["id"]

        async with TestSession() as session:
            task = await session.get(TaskModel, task_id)
            task.status = "completed"
            session.add_all([
                SourceModel(task_id=task_id, title="Old Source", content_snippet="old"),
                ReportModel(task_id=task_id, title="Old Report", content={"title": "old"}),
                TraceModel(task_id=task_id, agent_name="pipeline", events=[{"event": "old"}]),
                MetricsModel(task_id=task_id, source_count=1, claim_count=1, evidence_coverage_rate=1.0),
                ConstraintModel(task_id=task_id, constraint_value="old"),
            ])
            await session.commit()

        rerun = await client.post(f"/api/tasks/{task_id}/run")
        assert rerun.status_code == 202

        async with TestSession() as session:
            task = await session.get(TaskModel, task_id)
            assert task.status == "collecting"

            for model in (SourceModel, ReportModel, TraceModel, MetricsModel, ConstraintModel):
                result = await session.execute(model.__table__.select().where(model.task_id == task_id))
                assert result.first() is None

    async def test_status_endpoint(self, client: AsyncClient):
        resp = await client.post("/api/tasks", json={"target_product": "StatusTest"})
        task_id = resp.json()["id"]

        resp = await client.get(f"/api/tasks/{task_id}/status")
        assert resp.status_code == 200
        assert resp.json()["status"] == "pending"
        assert resp.json()["id"] == task_id
