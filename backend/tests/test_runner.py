"""Tests for task runner lifecycle persistence."""

import pytest

from app.models.database import MetricsModel, ReportModel, SourceModel, TaskModel, TraceModel
from app.orchestration import runner
from tests.conftest import TestSession


class SuccessfulGraph:
    def __init__(self, observed_statuses: list[str]):
        self.observed_statuses = observed_statuses

    async def astream(self, initial_state, stream_mode="updates"):
        assert stream_mode == "updates"

        yield {
            "collect": {
                "sources": [
                    {
                        "id": "src-1",
                        "type": "url",
                        "url": "https://example.com",
                        "title": "Source",
                        "content_snippet": "snippet",
                    }
                ],
                "traces": [
                    {"agent_name": "collector", "event_type": "output", "token_count": 3}
                ],
                "status": "analyzing",
            }
        }
        async with TestSession() as session:
            task = await session.get(TaskModel, initial_state["task_id"])
            self.observed_statuses.append(task.status)

        yield {
            "analyze": {
                "analysis": {"feature_trees": []},
                "traces": [
                    {"agent_name": "collector", "event_type": "output", "token_count": 3},
                    {"agent_name": "analyst", "event_type": "output", "token_count": 5},
                ],
                "status": "writing",
            }
        }
        async with TestSession() as session:
            task = await session.get(TaskModel, initial_state["task_id"])
            self.observed_statuses.append(task.status)

        yield {
            "write": {
                "report": {
                    "task_id": initial_state["task_id"],
                    "title": "Final Report",
                    "sections": [],
                },
                "traces": [
                    {"agent_name": "collector", "event_type": "output", "token_count": 3},
                    {"agent_name": "analyst", "event_type": "output", "token_count": 5},
                    {"agent_name": "writer", "event_type": "output", "token_count": 7},
                ],
                "status": "qa",
            }
        }
        async with TestSession() as session:
            task = await session.get(TaskModel, initial_state["task_id"])
            self.observed_statuses.append(task.status)

        yield {
            "qa": {
                "qa_feedback": {"passed": True},
                "metrics": {
                    "source_count": 1,
                    "claim_count": 2,
                    "evidence_coverage_rate": 1.0,
                },
                "traces": [
                    {"agent_name": "collector", "event_type": "output", "token_count": 3},
                    {"agent_name": "analyst", "event_type": "output", "token_count": 5},
                    {"agent_name": "writer", "event_type": "output", "token_count": 7},
                    {"agent_name": "qa", "event_type": "output", "token_count": 2},
                ],
                "status": "completed",
            }
        }


class FailingGraph:
    async def astream(self, initial_state, stream_mode="updates"):
        assert stream_mode == "updates"
        yield {
            "collect": {
                "sources": [],
                "traces": [
                    {"agent_name": "collector", "event_type": "output", "token_count": 1}
                ],
                "status": "analyzing",
            }
        }
        raise RuntimeError("pipeline boom")


@pytest.mark.asyncio
async def test_run_pipeline_persists_intermediate_statuses(monkeypatch):
    observed_statuses: list[str] = []
    monkeypatch.setattr(runner, "async_session", TestSession)
    monkeypatch.setattr(runner, "pipeline_graph", SuccessfulGraph(observed_statuses))

    async with TestSession() as session:
        task = TaskModel(target_product="RunnerSuccess", status="collecting")
        session.add(task)
        await session.commit()
        await session.refresh(task)
        task_id = task.id

    await runner.run_pipeline(task_id)

    async with TestSession() as session:
        task = await session.get(TaskModel, task_id)
        report = (await session.execute(ReportModel.__table__.select().where(ReportModel.task_id == task_id))).first()
        source = (await session.execute(SourceModel.__table__.select().where(SourceModel.task_id == task_id))).first()
        metrics = (await session.execute(MetricsModel.__table__.select().where(MetricsModel.task_id == task_id))).first()
        traces = (await session.execute(TraceModel.__table__.select().where(TraceModel.task_id == task_id))).first()

    assert observed_statuses == ["analyzing", "writing", "qa"]
    assert task.status == "completed"
    assert report is not None
    assert source is not None
    assert metrics is not None
    assert traces is not None
    assert traces.status == "completed"
    assert traces.total_tokens == 17


@pytest.mark.asyncio
async def test_run_pipeline_marks_failure_and_persists_failed_trace(monkeypatch):
    monkeypatch.setattr(runner, "async_session", TestSession)
    monkeypatch.setattr(runner, "pipeline_graph", FailingGraph())

    async with TestSession() as session:
        task = TaskModel(target_product="RunnerFailure", status="collecting")
        session.add(task)
        await session.commit()
        await session.refresh(task)
        task_id = task.id

    await runner.run_pipeline(task_id)

    async with TestSession() as session:
        task = await session.get(TaskModel, task_id)
        trace = (
            await session.execute(
                TraceModel.__table__.select().where(TraceModel.task_id == task_id)
            )
        ).first()

    assert task.status == "failed"
    assert trace is not None
    assert trace.status == "failed"
    assert trace.events[-1]["error_message"] == "pipeline boom"
