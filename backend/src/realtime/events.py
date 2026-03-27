"""
Dashboard websocket event broker.
"""
from __future__ import annotations

import asyncio
from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Any


class DashboardEventBroker:
    """Manage websocket subscribers and broadcast lightweight dashboard events."""

    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._subscribers: set[asyncio.Queue[dict[str, Any]]] = set()

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Bind the app event loop so sync handlers can publish safely."""
        self._loop = loop

    def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        """Register a subscriber queue."""
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=50)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        """Remove a subscriber queue."""
        self._subscribers.discard(queue)

    def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        """Broadcast an event to all connected subscribers."""
        if self._loop is None or not self._loop.is_running():
            return
        event = {
            "type": event_type,
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._loop.call_soon_threadsafe(self._broadcast_now, event)

    def _broadcast_now(self, event: dict[str, Any]) -> None:
        stale: list[asyncio.Queue[dict[str, Any]]] = []
        for queue in self._active_subscribers():
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                try:
                    queue.get_nowait()
                    queue.put_nowait(event)
                except asyncio.QueueEmpty:
                    stale.append(queue)
        for queue in stale:
            self.unsubscribe(queue)

    def _active_subscribers(self) -> Iterable[asyncio.Queue[dict[str, Any]]]:
        return tuple(self._subscribers)


dashboard_events = DashboardEventBroker()


def publish_dashboard_event(event_type: str, payload: dict[str, Any]) -> None:
    """Convenience wrapper for dashboard broadcasts."""
    dashboard_events.publish(event_type, payload)

