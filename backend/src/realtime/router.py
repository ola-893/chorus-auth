"""
Realtime websocket routes for the auth control plane dashboard.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from .events import dashboard_events

router = APIRouter()


@router.websocket("/ws/dashboard")
async def dashboard_socket(websocket: WebSocket) -> None:
    """Push dashboard events and heartbeat signals to connected clients."""
    await websocket.accept()
    queue = dashboard_events.subscribe()
    await websocket.send_json(
        {
            "type": "dashboard.connected",
            "payload": {"status": "ok"},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )

    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=20)
                await websocket.send_json(event)
            except asyncio.TimeoutError:
                await websocket.send_json(
                    {
                        "type": "dashboard.heartbeat",
                        "payload": {"status": "alive"},
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                )
    except WebSocketDisconnect:
        pass
    finally:
        dashboard_events.unsubscribe(queue)

