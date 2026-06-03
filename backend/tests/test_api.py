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
        assert node_ids == {"collect", "analyze", "write", "screenshot", "filter", "qa"}

        # Check node fields
        for n in data["nodes"]:
            assert "id" in n
            assert "label" in n
            assert "type" in n
            assert "status" in n

        # Check edges include forward flow + retry edges
        edge_pairs = {(e["source"], e["target"]) for e in data["edges"]}
        assert ("collect", "analyze") in edge_pairs
        assert ("qa", "collect") in edge_pairs
        assert ("qa", "analyze") in edge_pairs
        assert ("qa", "write") in edge_pairs

        # Pending task → all nodes pending
        statuses = {n["id"]: n["status"] for n in data["nodes"]}
        assert all(s == "pending" for s in statuses.values())

    async def test_get_dag_not_found(self, client: AsyncClient):
        resp = await client.get("/api/tasks/nonexistent/dag")
        assert resp.status_code == 404
