"""
Simple in-memory event bus for decoupling components.
"""
from typing import Callable, Dict, List, Any
import asyncio
from .logging_config import get_agent_logger

agent_logger = get_agent_logger(__name__)

class EventBus:
    def __init__(self):
        self.subscribers: Dict[str, List[Callable[[Any], None]]] = {}
        self.main_loop: Optional[asyncio.AbstractEventLoop] = None

    def set_main_loop(self, loop: asyncio.AbstractEventLoop):
        self.main_loop = loop

    def subscribe(self, event_type: str, callback: Callable[[Any], None]):
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback)

    def publish(self, event_type: str, data: Any):
        if event_type in self.subscribers:
            for callback in self.subscribers[event_type]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        try:
                            # Try getting current loop (works if called from main thread)
                            loop = asyncio.get_running_loop()
                            loop.create_task(callback(data))
                        except RuntimeError:
                            # Background thread, use run_coroutine_threadsafe with main loop
                            if self.main_loop and self.main_loop.is_running():
                                asyncio.run_coroutine_threadsafe(callback(data), self.main_loop)
                    else:
                        callback(data)
                except Exception as e:
                    agent_logger.log_system_error(e, "event_bus", "publish", context={"event": event_type})

# Global instance
event_bus = EventBus()
