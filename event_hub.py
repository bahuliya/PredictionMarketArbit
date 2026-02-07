import asyncio
from typing import Any, Dict

class EventHub:
    def __init__(self):
        self.queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()

    def publish(self, event: Dict[str, Any]) -> None:
        # Non-async publisher so you can call from your existing sync code
        try:
            self.queue.put_nowait(event)
        except Exception:
            # If queue is closed or loop is shutting down, ignore
            pass
