"""Tests for POST /api/tasks/{id}/run endpoint."""

import pytest
from sqlalchemy import select
from app.models.database import (
    SourceModel,
    ReportModel,
    TraceModel,
    ConstraintModel,
    MetricsModel,
)


class TestRunEndpoint:
    async def test_create_and_run_task(self, client, session):
        # Create a task
        resp = await client.post("/api/tasks", json={
            "industry": "SaaS",
            "target_product": "TestProduct",
            "competitors": ["CompA", "CompB"],
        })
        assert resp.status_code == 201
        task_id = resp.json()["id"]

        # Run the task
        run_resp = await client.post(f"/api/tasks/{task_id}/run")
        assert run_resp.status_code == 200
        data = run_resp.json()
        assert data["status"] == "completed"

        # Verify sources persisted
        result = await session.execute(
            select(SourceModel).where(SourceModel.task_id == task_id)
        )
        sources = result.scalars().all()
        assert len(sources) > 0

        # Verify report persisted
        result = await session.execute(
            select(ReportModel).where(ReportModel.task_id == task_id)
        )
        report = result.scalars().first()
        assert report is not None
        assert report.title != ""

        # Verify traces persisted
        result = await session.execute(
            select(TraceModel).where(TraceModel.task_id == task_id)
        )
        traces = result.scalars().all()
        assert len(traces) >= 4  # at least collector, analyst, writer, qa

        # Verify constraints persisted (ratchet mechanism)
        result = await session.execute(
            select(ConstraintModel).where(ConstraintModel.task_id == task_id)
        )
        constraints = result.scalars().all()
        assert len(constraints) > 0

        # Verify metrics persisted
        result = await session.execute(
            select(MetricsModel).where(MetricsModel.task_id == task_id)
        )
        metrics = result.scalars().first()
        assert metrics is not None
        assert metrics.source_count > 0

    async def test_run_nonexistent_task(self, client):
        resp = await client.post("/api/tasks/nonexistent/run")
        assert resp.status_code == 404

    async def test_run_already_completed_task(self, client):
        # Create and run
        resp = await client.post("/api/tasks", json={
            "target_product": "X",
            "competitors": ["Y"],
        })
        task_id = resp.json()["id"]
        await client.post(f"/api/tasks/{task_id}/run")

        # Try to run again
        resp2 = await client.post(f"/api/tasks/{task_id}/run")
        assert resp2.status_code == 409

    async def test_report_visible_after_run(self, client):
        # Create and run
        resp = await client.post("/api/tasks", json={
            "target_product": "ReportTest",
            "competitors": ["Comp1"],
        })
        task_id = resp.json()["id"]
        await client.post(f"/api/tasks/{task_id}/run")

        # Check report endpoint
        report_resp = await client.get(f"/api/tasks/{task_id}/report")
        assert report_resp.status_code == 200
        assert report_resp.json()["title"] != ""

    async def test_traces_visible_after_run(self, client):
        resp = await client.post("/api/tasks", json={
            "target_product": "TraceTest",
            "competitors": ["Comp1"],
        })
        task_id = resp.json()["id"]
        await client.post(f"/api/tasks/{task_id}/run")

        traces_resp = await client.get(f"/api/tasks/{task_id}/traces")
        assert traces_resp.status_code == 200
        traces = traces_resp.json()
        assert len(traces) >= 4

    async def test_sources_visible_after_run(self, client):
        resp = await client.post("/api/tasks", json={
            "target_product": "SourceTest",
            "competitors": ["Comp1"],
        })
        task_id = resp.json()["id"]
        await client.post(f"/api/tasks/{task_id}/run")

        sources_resp = await client.get(f"/api/tasks/{task_id}/sources")
        assert sources_resp.status_code == 200
        sources = sources_resp.json()
        assert len(sources) > 0
