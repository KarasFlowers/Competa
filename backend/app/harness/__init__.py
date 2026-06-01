"""Harness — Five-Layer Architecture for Multi-Agent Systems.

This package provides an explicit architectural layering of Competa's
multi-agent system, inspired by the CompetitorLens Harness pattern.

Layers:
  L1 Runtime   — Agent execution loop, retry, error recovery
  L2 Context   — Shared state, token budget, context window management
  L3 Capability — Tool registry, search backends, screenshot service
  L4 Governance — Schema validation, audit logging, permission guard, secret redaction
  L5 Surface   — DAG orchestration, event bus, SSE streaming

Each layer re-exports the relevant existing modules so that new code can
import from a single, semantically meaningful namespace:

    from app.harness.runtime import BaseAgent
    from app.harness.governance import validate_output, redact_secrets
    from app.harness.surface import run_pipeline, publish_event
"""
