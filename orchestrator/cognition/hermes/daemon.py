"""Phase 6+ Velocity Hardening: Hermes daemon lifecycle wrapper.

Doctrine anchor: docs/HERMES_SPIKE_RESULT.md § 1.
Wraps request-scoped Hermes agents in a long-lived asyncio task loop that manages
wake/sleep cycles and feeds them from the SENSORIUM_LEDGER.
"""
import asyncio
from typing import Any, Callable, Coroutine

class DaemonWrapper:
    def __init__(self, name: str, run_cycle: Callable[[], Coroutine[Any, Any, None]], sleep_s: float = 60.0):
        self.name = name
        self.run_cycle = run_cycle
        self.sleep_s = sleep_s
        self._task: asyncio.Task[None] | None = None
        self._running = False

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop(), name=f"hermes-daemon-{self.name}")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _loop(self) -> None:
        while self._running:
            try:
                await self.run_cycle()
            except Exception as e:
                import sys
                print(f"State-of-Xion: Daemon {self.name} cycle failed: {e}", file=sys.stderr)
            await asyncio.sleep(self.sleep_s)
