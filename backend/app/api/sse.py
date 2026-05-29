"""Server-Sent Events endpoint for real-time pipeline progress."""

from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Simple in-memory event bus
# ---------------------------------------------------------------------------

# task_id -> list of asyncio.Queue
_subscribers: dict[str, list[asyncio.Queue[str]]] = defaultdict(list)


def publish_event(task_id: str, event: dict) -> None:
    """Push an event dict to all subscribers for a task."""
    payload = json.dumps(event, ensure_ascii=False)
    for q in _subscribers.get(task_id, []):
        q.put_nowait(payload)


def subscribe(task_id: str) -> asyncio.Queue[str]:
    """Create a new subscriber queue for a task."""
    q: asyncio.Queue[str] = asyncio.Queue(maxsize=64)
    _subscribers[task_id].append(q)
    return q


def unsubscribe(task_id: str, q: asyncio.Queue[str]) -> None:
    """Remove a subscriber queue."""
    subs = _subscribers.get(task_id, [])
    if q in subs:
        subs.remove(q)
    if not subs:
        _subscribers.pop(task_id, None)


# ---------------------------------------------------------------------------
# SSE endpoint
# ---------------------------------------------------------------------------

@router.get("/{task_id}/events")
async def task_events(task_id: str, request: Request):
    """Stream pipeline progress events for a task via SSE."""

    async def event_generator():
        q = subscribe(task_id)
        try:
            # Send initial connection event
            yield f"event: connected\ndata: {{\"task_id\": \"{task_id}\"}}\n\n"

            while True:
                if await request.is_disconnected():
                    break
                try:
                    data = await asyncio.wait_for(q.get(), timeout=30)
                    yield f"event: progress\ndata: {data}\n\n"
                except asyncio.TimeoutError:
                    # Send keep-alive
                    yield f": keep-alive\n\n"
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
