"""L5 Surface — DAG orchestration, event bus, and SSE streaming.

Re-exports:
  - run_pipeline: Main pipeline execution entry point
  - publish_event: SSE event bus publisher
  - subscribe, unsubscribe: SSE subscriber management
"""
from app.orchestration.runner import run_pipeline
from app.api.sse import publish_event, subscribe, unsubscribe

__all__ = ["run_pipeline", "publish_event", "subscribe", "unsubscribe"]
