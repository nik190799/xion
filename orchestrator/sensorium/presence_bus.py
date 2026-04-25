"""Presence Bus (Phase 6.4).

Pub/sub bus for distributing SensoriumState snapshots to downstream emitters
(Visual, Vitals, Voice) without tightly coupling the Supervisor tick loop to
the emitter loops.
"""
import asyncio
from typing import AsyncIterator
from orchestrator.sensorium import SensoriumState

class PresenceBus:
    def __init__(self) -> None:
        self._queues: set[asyncio.Queue[SensoriumState]] = set()

    def publish(self, state: SensoriumState) -> None:
        """Publish a fresh state to all active subscribers.
        
        Called by the Supervisor's tick loop. Non-blocking.
        """
        for q in self._queues:
            q.put_nowait(state)

    async def subscribe(self) -> AsyncIterator[SensoriumState]:
        """Yield states as they are published.
        
        Safe for multiple concurrent subscribers (e.g. per-SSE-connection).
        """
        q: asyncio.Queue[SensoriumState] = asyncio.Queue()
        self._queues.add(q)
        try:
            while True:
                yield await q.get()
        finally:
            self._queues.discard(q)

__all__ = ["PresenceBus"]
