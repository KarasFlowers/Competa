"""Shared state definition for the LangGraph pipeline."""

from __future__ import annotations

from typing import Any, TypedDict


class PipelineState(TypedDict, total=False):
    task_id: str
    task: dict[str, Any]
    sources: list[dict[str, Any]]
    survey: dict[str, Any]
    interview: dict[str, Any]
    fieldwork: dict[str, Any]
    analysis: dict[str, Any]
    report: dict[str, Any]
    qa_feedback: dict[str, Any]
    metrics: dict[str, Any]
    previous_metrics: dict[str, Any]
    handoff: dict[str, Any]
    traces: list[dict[str, Any]]
    status: str
    error: str
    retry_count: int
    constraints: list[str]
    screenshot_paths: list[dict[str, str | None]]
