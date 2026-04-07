"""In-memory pub/sub for streaming build events to SSE clients."""

import asyncio
import json
import time
from collections import defaultdict

# Per-build event queues: build_id -> list of asyncio.Queue
_subscribers: dict[str, list[asyncio.Queue]] = defaultdict(list)


def publish(build_id: str, event_type: str, data: dict):
    """Publish an event to all SSE subscribers for a build."""
    event = {
        "type": event_type,
        "timestamp": time.time(),
        **data,
    }
    for queue in _subscribers.get(build_id, []):
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            pass  # drop if client is too slow


def subscribe(build_id: str) -> asyncio.Queue:
    """Subscribe to events for a build. Returns a Queue to read from."""
    queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    _subscribers[build_id].append(queue)
    return queue


def unsubscribe(build_id: str, queue: asyncio.Queue):
    """Remove a subscriber."""
    if build_id in _subscribers:
        try:
            _subscribers[build_id].remove(queue)
        except ValueError:
            pass
        if not _subscribers[build_id]:
            del _subscribers[build_id]
