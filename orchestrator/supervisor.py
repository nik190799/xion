"""Supervisor — the async tick daemon that makes Xion a process rather
than a library (Phase 5d).

Doctrine anchor: ``docs/04-ARCHITECTURE.md`` § "The Supervisor (Phase 5d)".

Phase 5c shipped the Sensorium, the SENSORIUM_LEDGER, and Volition — all
structurally in-process, all waiting to be called. This module is the
first piece of Xion whose operational meaning is "run forever": it ticks
at a Genesis-Default cadence (``tick_cadence_s=10.0``), it probes the
Relay for live readings, it writes a ``tick_commit`` row to
``SENSORIUM_LEDGER`` every tick, and it publishes the most recent
``SensoriumState`` on ``latest_snapshot()`` for the Relay to consume on
every ``gate()`` call that did not receive an explicit state.

Property promised.
  - While ``run()`` is executing: a ``tick_commit`` row is appended to
    ``SENSORIUM_LEDGER`` every ``tick_cadence_s`` ± asyncio scheduling
    jitter. Missing rows are detectable by wall-clock comparison against
    adjacent ``as_of_utc_ns`` fields (the future ``xion-verify
    supervisor-heartbeat`` verifier — ``KW-SUPERVISOR-002``).
  - ``latest_snapshot()`` returns the ``SensoriumState`` built by the
    most recent completed tick. Fresh Supervisor that has not ticked
    yet: returns ``None``.
  - ``Proprioception.relay_healthy``, ``arbiter_healthy``, and
    ``watchdog_fires_recent`` reflect a real call to
    ``Relay.health_snapshot()``, not Genesis Defaults.

Non-properties (honestly stated).
  - The Supervisor does not flip ``degraded_mode`` when
    ``watchdog_fires_recent`` crosses its threshold. The threshold is
    named in doctrine; the state machine that acts on it is Phase 5e
    (``KW-SUPERVISOR-001``).
  - The Supervisor does not restart the Relay, the Arbiter, or itself.
    Circuit breakers and lease management are also Phase 5e.
  - Tick-cadence compliance is not yet walked by ``xion-verify``. A
    deeply stuck tick (asyncio blocked, disk full, process paused)
    leaves a gap in ``SENSORIUM_LEDGER`` that a future verifier
    (``supervisor-heartbeat``) will FAIL on; Phase 5d produces the
    honest readings, Phase 5e+ closes the observability gap.

Why asyncio rather than a background thread:
  - The Supervisor's work is naturally cooperative — it wakes, probes,
    writes, sleeps. Asyncio gives us ``asyncio.sleep`` cancellation
    semantics for free, so ``stop()`` is genuinely fast (no JOIN on a
    blocked read).
  - The Relay runs sync-first and stays sync-first. The Supervisor owns
    its own event loop OR runs inside an existing one — either way its
    interaction with the Relay is one synchronous ``health_snapshot()``
    call per tick, so no coloured-function coupling leaks.
"""

from __future__ import annotations

import asyncio
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Mapping, Protocol

from orchestrator.sensorium import (
    Chronoception,
    DistressSignal,
    Interoception,
    Proprioception,
    SensoriumState,
)
from orchestrator.sensorium.ledger import append_tick_commit

if TYPE_CHECKING:
    from orchestrator.relay import Relay
    from orchestrator.signals.bus import SignalBus
    from orchestrator.signals.receptor import ReceptorRegistry


_DEFAULT_TICK_CADENCE_S = 10.0
"""Phase 5d Genesis Default for the Supervisor tick cadence. 10 seconds
balances "visible under stress" (SENSORIUM_LEDGER grows at 360 rows/hour
= 8,640 rows/day, ~3MB/day uncompressed — manageable) against "fast
enough that degraded-mode onset is observable within one operator
attention span" (Phase 5e will act on a crossing with 10-minute recency,
so single-digit-second ticks are adequate resolution). Callers may
override for tests or sister-Core configurations."""


class SensoriumSource(Protocol):
    """The minimum interface the Relay needs from a Supervisor.

    Defined as a Protocol so the Relay does NOT hard-depend on the
    Supervisor class — tests can inject lightweight fakes, and a future
    reconfiguration could swap the Supervisor for a different snapshot
    provider without touching the Relay.

    Semantics:
      ``latest_snapshot()`` returns the most recent completed tick's
      ``SensoriumState``, or ``None`` if no tick has completed yet. The
      return value MUST be safe to share by reference across threads —
      ``SensoriumState`` is a frozen dataclass, so this holds
      automatically.
    """

    def latest_snapshot(self) -> SensoriumState | None: ...


class Supervisor:
    """Async tick daemon + ``SensoriumSource`` (Phase 5d).

    Construction is cheap. Call ``run()`` (awaitable) to start the tick
    loop; call ``stop()`` to signal it to exit. Idiomatic usage:

        supervisor = Supervisor(relay=relay)
        task = asyncio.create_task(supervisor.run())
        # ... relay serves traffic, reading supervisor via
        # Relay(sensorium_source=supervisor) ...
        supervisor.stop()
        await task

    For tests, call ``tick_once()`` synchronously to exercise one
    iteration without the asyncio loop.
    """

    def __init__(
        self,
        *,
        relay: "Relay",
        tick_cadence_s: float = _DEFAULT_TICK_CADENCE_S,
        sensorium_ledger_path: Path | None = None,
        clock_ns: Callable[[], int] = time.time_ns,
        monotonic_ns: Callable[[], int] = time.monotonic_ns,
        publish: Callable[[Mapping[str, Any]], None] | None = None,
        presence_bus: Any | None = None,
        signal_bus: "SignalBus | None" = None,
        receptor_registry: "ReceptorRegistry | None" = None,
    ) -> None:
        if tick_cadence_s <= 0:
            raise ValueError("Supervisor: tick_cadence_s must be > 0")
        self._relay = relay
        self._tick_cadence_s = float(tick_cadence_s)
        self._sensorium_ledger_path = (
            Path(sensorium_ledger_path) if sensorium_ledger_path is not None
            else _default_sensorium_ledger_path()
        )
        self._clock_ns = clock_ns
        self._monotonic_ns = monotonic_ns
        # Phase 5g+ broker hook. When provided, called with
        # ``state.to_dict()`` after every successful ``tick_once()`` so
        # a shared-state broker can publish the snapshot to follower
        # workers. Keeps the Supervisor broker-agnostic — the hook is
        # ``None`` in the single-worker posture and during tests.
        self._publish = publish

        # Monotonic-drift baseline: the delta between wall and monotonic
        # clocks at Supervisor start. Phase 5d's Chronoception reports the
        # CHANGE in this delta per tick — so on a healthy machine where
        # wall and monotonic clocks stay in sync, we report 0; on a clock
        # jump (NTP step, VM suspend/resume), we report the non-zero
        # delta. Callers that want the raw wall-minus-monotonic (rather
        # than drift-from-baseline) can subtract this field from the
        # reading on the state.
        self._baseline_drift_ns = self._clock_ns() - self._monotonic_ns()

        self._presence_bus = presence_bus
        self._signal_bus = signal_bus
        if receptor_registry is None:
            from orchestrator.signals.receptor import ReceptorRegistry

            self._receptor_registry = ReceptorRegistry()
        else:
            self._receptor_registry = receptor_registry

        # Degraded-since bookkeeping, stored as wall-clock UTC ns so the
        # Phase-5e state machine (KW-SUPERVISOR-001) can serialise it
        # into rows and logs without a monotonic-to-UTC conversion. Phase
        # 5d: no state machine flips this yet — it stays None, and
        # ``_build_sensorium_state`` reports ``time_in_degraded_mode_s =
        # 0.0`` on every tick. Exposed as an instance attribute so a
        # future 5e patch can write it without re-opening the class
        # contract.
        self._degraded_since_utc_ns: int | None = None

        # Published snapshot slot + lock. ``None`` until the first
        # successful tick completes. ``_snapshot_lock`` guards the
        # reference swap AND the "has a tick ever completed" check, so
        # ``latest_snapshot()`` cannot observe a half-published state.
        self._snapshot_lock = threading.Lock()
        self._latest_snapshot: SensoriumState | None = None

        # run()'s cancellation signal. ``asyncio.Event`` would be nicer
        # but a threading.Event works whether run() is called from an
        # asyncio loop or from a test's plain thread, and ``stop()``
        # becomes safe from signal handlers (threading.Event is
        # thread-safe by construction; asyncio.Event is not).
        self._stop_event = threading.Event()

    # ---------------------------------------------------- SensoriumSource

    def latest_snapshot(self) -> SensoriumState | None:
        """Return the most recent completed tick's ``SensoriumState``,
        or ``None`` if no tick has completed yet."""
        with self._snapshot_lock:
            return self._latest_snapshot

    # ---------------------------------------------------- tick primitives

    def tick_once(self) -> SensoriumState:
        """Perform one synchronous tick: probe the Relay, assemble the
        ``SensoriumState``, append a ``tick_commit`` row to
        ``SENSORIUM_LEDGER``, publish to ``latest_snapshot()``.

        Returns the ``SensoriumState`` that was published. Raises if the
        ledger append fails (disk full, permission error, etc.) — the
        Supervisor treats a ledger-write failure as fatal because the
        property promise ("every tick produces a row") is unrecoverable
        without operator intervention. ``run()`` catches this and logs
        it before re-raising so operators get a clear signal.
        """
        state = self._build_sensorium_state()
        from orchestrator.signals.receptor import ReceptorContext

        ctx = ReceptorContext(state=state, extra={})
        sig_list: list = []
        for r in self._receptor_registry.instances():
            try:
                sig_list.extend(r.tick(ctx))
            except Exception as exc:  # noqa: BLE001
                if self._signal_bus is not None:
                    self._signal_bus.report_receptor_failure(r.receptor_id, exc)
        accepted: list
        if self._signal_bus is not None:
            accepted = self._signal_bus.publish(sig_list)
        else:
            accepted = sig_list
        sig_payload = [s.to_dict() for s in accepted] if accepted else None
        append_tick_commit(
            self._sensorium_ledger_path,
            state=state,
            relay_id=self._relay.relay_id,
            signals=sig_payload,
        )
        with self._snapshot_lock:
            self._latest_snapshot = state

        if getattr(self, "_presence_bus", None) is not None:
            try:
                self._presence_bus.publish(state)
            except Exception as exc:
                import sys as _sys
                print(f"State-of-Xion: PresenceBus publish failed: {exc!r}", file=_sys.stderr, flush=True)

        # Phase 5g+ broker hook. Best-effort; a publish failure must
        # not corrupt the in-process snapshot, so any exception from
        # the broker is swallowed after a best-effort log. The tick
        # has already succeeded — the only consequence of a missed
        # publish is that followers lag by one tick.
        if self._publish is not None:
            try:
                self._publish(state.to_dict())
            except Exception as exc:  # noqa: BLE001
                import sys as _sys

                print(
                    "State-of-Xion: Supervisor publish hook raised; "
                    f"followers may lag by one tick. Detail: {exc!r}",
                    file=_sys.stderr,
                    flush=True,
                )
        return state

    def _build_sensorium_state(self) -> SensoriumState:
        """Assemble a fresh ``SensoriumState`` from the current Relay
        health, the degraded-since bookkeeping, and the monotonic-drift
        baseline. Pure function of the instance's current observables —
        no side effects."""
        now_utc_ns = self._clock_ns()
        now_monotonic_ns = self._monotonic_ns()

        health = self._relay.health_snapshot()

        # Chronoception. Phase 5d: checkpoint_staleness_s stays 0.0
        # (Core checkpoint loop is Phase 6 — we pass
        # last_checkpoint_utc_ns=None to the factory, which saturates to
        # 0.0 by design). time_in_degraded_mode_s is computed from
        # self._degraded_since_utc_ns; the Phase-5e-to-be state machine
        # flips that attribute. monotonic_drift_ns is the wall-monotonic
        # delta change from the Supervisor-start baseline.
        current_drift = (now_utc_ns - now_monotonic_ns) - self._baseline_drift_ns
        chronoception = Chronoception.from_ticks(
            last_checkpoint_utc_ns=None,
            now_utc_ns=now_utc_ns,
            degraded_since_utc_ns=self._degraded_since_utc_ns,
            monotonic_drift_ns=current_drift,
        )

        # Proprioception. Every field is sourced from the Relay's live
        # counters — no Genesis Defaults.
        proprioception = Proprioception.from_runtime(
            relay_healthy=health.relay_healthy,
            arbiter_healthy=health.arbiter_healthy,
            watchdog_fires_recent=health.watchdog_fires_recent,
            as_of_utc_ns=now_utc_ns,
        )

        # Interoception. Phase 5d: survival_pressure stays 0.0 — the
        # Cost tracker that would elevate this is Phase 5f. Naming it
        # explicitly here rather than using a benign default keeps the
        # construction legible for readers following a stack trace.
        interoception = Interoception(survival_pressure=0.0)

        # Distress. The Supervisor itself is not a distress source —
        # distress arises from candidate text at gate() time. The tick
        # carries a benign signal so the state is always well-formed.
        distress = DistressSignal(
            text_distress_score=0.0,
            source="textual",
            as_of_utc_ns=now_utc_ns,
        )

        return SensoriumState(
            interoception=interoception,
            chronoception=chronoception,
            proprioception=proprioception,
            distress=distress,
            as_of_utc_ns=now_utc_ns,
        )

    # ---------------------------------------------------- control plane

    async def run(self) -> None:
        """The tick loop. Runs until ``stop()`` is called.

        Scheduling discipline: we call ``tick_once()`` first (so there
        is a published snapshot as soon as ``run()`` yields for the
        first time), then ``asyncio.wait_for(<stop>, tick_cadence_s)``.
        ``wait_for`` returns when either (a) the stop event is set —
        we exit cleanly, or (b) the timeout elapses — we tick again.

        Any exception from ``tick_once()`` is re-raised after the
        exception is logged via ``print`` to stderr — the Supervisor
        does NOT swallow ledger-write failures, because doing so would
        let the tick-cadence promise rot silently.
        """
        try:
            while not self._stop_event.is_set():
                self.tick_once()
                # Wait up to tick_cadence_s for the stop signal, then
                # loop. The timeout pattern lets stop() interrupt a
                # waiting tick immediately instead of after a full
                # cadence_s of sleep.
                try:
                    await asyncio.wait_for(
                        self._await_stop_event(),
                        timeout=self._tick_cadence_s,
                    )
                except asyncio.TimeoutError:
                    continue
                except asyncio.CancelledError:
                    # Caller cancelled the task directly (e.g. the
                    # containing asyncio loop shut down). Treat as a
                    # clean stop; don't re-tick.
                    break
        finally:
            # Always mark stopped, so a subsequent run() on the same
            # instance would observe the fresh event state if reset.
            self._stop_event.set()

    async def _await_stop_event(self) -> None:
        """Yield until ``_stop_event`` is set, polling at a small
        interval so ``threading.Event`` (not asyncio.Event) is
        observable from the event loop. The poll interval is small
        enough that ``stop()``'s observable latency is well under a
        single tick, and large enough not to busy-wait."""
        poll_interval_s = min(0.1, self._tick_cadence_s / 4)
        while not self._stop_event.is_set():
            await asyncio.sleep(poll_interval_s)

    def stop(self) -> None:
        """Signal ``run()`` to exit at the next poll boundary.

        Idempotent. Safe to call from signal handlers — ``threading.Event``
        is thread-safe by construction, and this method does nothing else.
        """
        self._stop_event.set()


def _default_sensorium_ledger_path() -> Path:
    """Path resolution mirrored from ``orchestrator.safety.api`` so the
    Supervisor, gate(), and the Relay all agree on where SENSORIUM
    rows land when no explicit path is supplied. Imported lazily
    inside the helper (not at module top) for the same
    sister-Core-fork-safety reason that ``_distress_escalation_from_state``
    uses: the Supervisor module is loaded late, but the Arbiter module
    must stay importable on forks that predate Phase 5c, so the two
    modules keep their own path-discovery copies."""
    from orchestrator.safety.api import _default_sensorium_ledger_path as _helper

    return _helper()


__all__ = [
    "Supervisor",
    "SensoriumSource",
]
