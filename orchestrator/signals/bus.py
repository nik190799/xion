from __future__ import annotations

import asyncio
import fnmatch
import queue
import threading
import time
from collections.abc import AsyncIterator, Callable
from typing import TYPE_CHECKING

from orchestrator.signals.envelope import Signal
from orchestrator.signals.schema import SignalSchemaError, validate_signal

if TYPE_CHECKING:
    from orchestrator.signals.reflex import ReflexRegistry


class SignalBus:
    """Thread-safe publish; async subscribe via executor-backed queue get."""

    def __init__(
        self,
        reflex_registry: ReflexRegistry | None = None,
        on_drop: Callable[[str, str], None] | None = None,
    ) -> None:
        self._reflex = reflex_registry
        self._on_drop = on_drop
        self._lock = threading.RLock()
        self._latest: dict[str, Signal] = {}
        # (glob patterns, SimpleQueue[Signal])
        self._subscribers: list[tuple[tuple[str, ...], queue.SimpleQueue[Signal]]] = []
        # degraded receptors / schema drops
        self._receptor_errors: list[str] = []

    @property
    def receptor_error_log(self) -> list[str]:
        with self._lock:
            return list(self._receptor_errors)

    def _record_receptor_degraded(self, receptor_id: str, msg: str) -> None:
        with self._lock:
            self._receptor_errors.append(f"{receptor_id}: {msg}")

    def _emit_bus_integrity(self, message: str, *, band: str = "warning") -> None:
        s = self._synthetic(
            "vital.bus_integrity",
            "signal_bus",
            message,
            band=band,
        )
        self._ingest_one(s, validate=False)

    def _synthetic(
        self,
        kind: str,
        source: str,
        value: str,
        *,
        band: str,
    ) -> Signal:
        return Signal(
            kind=kind,
            source=source,
            value=value,
            timestamp_utc_ns=time.time_ns(),
            methodology_hash="0000000000000000000000000000000000000000000000000000000000000000",
            confidence=1.0,
            band=band,
            schema_version=1,
        )

    def _ingest_one(self, s: Signal, *, validate: bool) -> bool:
        if validate:
            try:
                validate_signal(s)
            except SignalSchemaError as e:
                self._emit_bus_integrity(f"drop:{s.kind!s}:{e}", band="critical")
                if self._on_drop:
                    self._on_drop(s.kind, str(e))
                return False
        with self._lock:
            self._latest[s.kind] = s
        if self._reflex is not None:
            self._reflex.dispatch(s)
        for patterns, q in self._subscribers:
            if any(fnmatch.fnmatch(s.kind, p) for p in patterns):
                q.put(s)
        return True

    def publish(
        self,
        signals: list[Signal],
    ) -> list[Signal]:
        """Validate and store signals; return the accepted list (in order)."""
        accepted: list[Signal] = []
        for s in signals:
            if self._ingest_one(s, validate=True):
                accepted.append(s)
        return accepted

    def report_receptor_failure(self, receptor_id: str, exc: BaseException) -> None:
        self._record_receptor_degraded(receptor_id, repr(exc))
        self._emit_bus_integrity(f"receptor_error:{receptor_id}:{exc!r}", band="warning")

    async def subscribe(self, *kind_patterns: str) -> AsyncIterator[Signal]:
        if not kind_patterns:
            kind_patterns = ("*",)
        q: queue.SimpleQueue[Signal] = queue.SimpleQueue()
        with self._lock:
            self._subscribers.append((kind_patterns, q))
        try:
            loop = asyncio.get_running_loop()
            while True:
                s = await loop.run_in_executor(None, q.get)
                yield s
        finally:
            with self._lock:
                self._subscribers = [
                    p for p in self._subscribers if p[1] is not q
                ]

    def latest(self, kind: str) -> Signal | None:
        with self._lock:
            return self._latest.get(kind)

    def latest_by_category(self, category: str) -> dict[str, Signal]:
        with self._lock:
            return {
                k: v
                for k, v in self._latest.items()
                if k.split(".", 1)[0] == category
            }

    def latest_all(self) -> dict[str, Signal]:
        with self._lock:
            return dict(self._latest)

    def clear_for_tests(self) -> None:
        with self._lock:
            self._latest.clear()
            self._receptor_errors.clear()
            self._subscribers.clear()
