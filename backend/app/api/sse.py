"""Server-Sent Events endpoint for real-time pipeline progress."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import defaultdict

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Simple in-memory event bus with stale-subscriber cleanup
# ---------------------------------------------------------------------------

# task_id -> list of (asyncio.Queue, last_active_timestamp)
_subscribers: dict[str, list[tuple[asyncio.Queue[str], float]]] = defaultdict(list)

# Maximum idle seconds before a subscriber is considered stale
_STALE_TTL_SECONDS = 120


def publish_event(task_id: str, event: dict) -> None:
    """Push an event dict to all subscribers for a task."""
    payload = json.dumps(event, ensure_ascii=False)
    for q, _ts in _subscribers.get(task_id, []):
        try:
            q.put_nowait(payload)
        except asyncio.QueueFull:
            pass  # drop event if subscriber is too slow


def subscribe(task_id: str) -> asyncio.Queue[str]:
    """Create a new subscriber queue for a task."""
    q: asyncio.Queue[str] = asyncio.Queue(maxsize=64)
    _subscribers[task_id].append((q, time.monotonic()))
    return q


def unsubscribe(task_id: str, q: asyncio.Queue[str]) -> None:
    """Remove a subscriber queue."""
    subs = _subscribers.get(task_id, [])
    _subscribers[task_id] = [(sq, ts) for sq, ts in subs if sq is not q]
    if not _subscribers[task_id]:
        _subscribers.pop(task_id, None)


def _cleanup_stale_subscribers() -> None:
    """Remove subscriber queues that haven't been active within the TTL."""
    now = time.monotonic()
    stale_task_ids: list[str] = []
    for task_id, subs in _subscribers.items():
        fresh = [(q, ts) for q, ts in subs if now - ts < _STALE_TTL_SECONDS]
        if fresh:
            _subscribers[task_id] = fresh
        else:
            stale_task_ids.append(task_id)
    for tid in stale_task_ids:
        _subscribers.pop(tid, None)


# ---------------------------------------------------------------------------
# SSE endpoint
# ---------------------------------------------------------------------------

@router.get("/{task_id}/events")
async def task_events(task_id: str, request: Request):
    """Stream pipeline progress events for a task via SSE."""

    async def event_generator():
        q = subscribe(task_id)
        # Run stale cleanup on each new connection
        _cleanup_stale_subscribers()
        try:
            # Send initial connection event
            yield f"event: connected\ndata: {{\"task_id\": \"{task_id}\"}}\n\n"

            while True:
                if await request.is_disconnected():
                    break
                try:
                    data = await asyncio.wait_for(q.get(), timeout=30)
                    # Update activity timestamp on successful delivery
                    subs = _subscribers.get(task_id, [])
                    now = time.monotonic()
                    _subscribers[task_id] = [(sq, now) if sq is q else (sq, ts) for sq, ts in subs]
                    yield f"event: progress\ndata: {data}\n\n"
                except asyncio.TimeoutError:
                    # Send keep-alive and update activity timestamp
                    yield f": keep-alive\n\n"
                    subs = _subscribers.get(task_id, [])
                    now = time.monotonic()
                    _subscribers[task_id] = [(sq, now) if sq is q else (sq, ts) for sq, ts in subs]
        finally:
            unsubscribe(task_id, q)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
