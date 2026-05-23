"""Graph state definition — TypedDict shared across all DAG nodes.

Inspired by LangGraph StateGraph pattern with typed state management.
"""

from __future__ import annotations

from typing import Any, TypedDict


class GraphState(TypedDict, total=False):
    """Shared state for the competitive analysis DAG.

    All agents read from and write to this state.
    LangGraph merges the returned dict into the current state after each node.
    """

    # --- Task context (set at start, read-only during execution) ---
    task_id: str
    industry: str
    target_product: str
    competitors: list[str]

    # --- Agent outputs (populated during execution) ---
    sources: list[dict[str, Any]]           # CollectorAgent output
    analysis: dict[str, Any] | None         # AnalystAgent output
    report: dict[str, Any] | None           # WriterAgent output
    qa_feedback: dict[str, Any] | None      # QAAgent output

    # --- Ratchet mechanism ---
    constraints: list[dict[str, Any]]       # Accumulated ConstraintRule dicts

    # --- Observability ---
    traces: list[Any]                       # AgentTrace objects

    # --- Control flow ---
    retry_count: int                        # Current retry count
    max_retries: int                        # Max allowed retries (default 2)
