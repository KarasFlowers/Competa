"""Tests for the FastAPI endpoints."""

from httpx import AsyncClient


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

    async def test_sources_empty(self, client: AsyncClient):
        resp = await client.post("/api/tasks", json={"target_product": "Y"})
        task_id = resp.json()["id"]
        resp = await client.get(f"/api/tasks/{task_id}/sources")
        assert resp.status_code == 200
        assert resp.json() == []


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

    async def test_run_returns_202(self, client: AsyncClient):
        resp = await client.post("/api/tasks", json={"target_product": "TestProd"})
        task_id = resp.json()["id"]

        resp = await client.post(f"/api/tasks/{task_id}/run")
        assert resp.status_code == 202
        assert resp.json()["task_id"] == task_id

    async def test_run_conflict_if_not_pending(self, client: AsyncClient):
        """Tasks not in pending/failed state should reject /run."""
        resp = await client.post("/api/tasks", json={"target_product": "TestProd2"})
        task_id = resp.json()["id"]

        # Manually set status to 'collecting' via DB to simulate running state
        from tests.conftest import TestSession
        from app.models.database import TaskModel

        async with TestSession() as session:
            task = await session.get(TaskModel, task_id)
            task.status = "collecting"
            await session.commit()

        # Should reject with 409
        resp = await client.post(f"/api/tasks/{task_id}/run")
        assert resp.status_code == 409

    async def test_status_endpoint(self, client: AsyncClient):
        resp = await client.post("/api/tasks", json={"target_product": "StatusTest"})
        task_id = resp.json()["id"]

        resp = await client.get(f"/api/tasks/{task_id}/status")
        assert resp.status_code == 200
        assert resp.json()["status"] == "pending"
        assert resp.json()["id"] == task_id
