"""Phase 5g+: the broker-backed Supervisor lifecycle shell.

Doctrine anchors:
    docs/04-ARCHITECTURE.md § "Multi-worker coherence (Phase 5g+)"
    docs/33-MULTI-WORKER.md § "Lease semantics"

A :class:`BrokerSupervisorShell` owns one worker's broker-mediated
lifecycle. It runs either:

- **As leader.** Ticks the Supervisor, writes ``tick_commit`` rows to
  ``SENSORIUM_LEDGER``, publishes the snapshot to the broker, renews
  the lease on a ``leader_renew_s`` cadence. If a renewal returns
  ``False`` (lease expired or was clobbered), it demotes itself and
  returns to follower mode.
- **As follower.** Reads the broker's latest snapshot on each
  :meth:`latest_snapshot` call, deserializing into :class:`SensoriumState`.
  On a cadence, probes :meth:`Broker.try_acquire_leader`; when that
  succeeds, promotes itself and begins ticking.

The shell exposes the same external surface a :class:`Supervisor`
exposes to the FastAPI lifespan and to the :class:`Relay`:
``latest_snapshot()``, ``tick_once()`` (leader-only; raises if the
shell is a follower at call time), ``run()`` (the async loop), and
``stop()``. This lets the lifespan treat leader and follower
identically — the same ``app.state.supervisor`` assignment, the same
``supervisor.run()`` task, the same shutdown path.

Rationale for one shell class rather than two:

Shipping separate leader and follower classes would force the lifespan
to know which kind to construct, and a promotion (follower → leader)
would require a class swap mid-lifespan. One shell that carries both
modes keeps the lifespan ignorant of the dynamic role.

What this module deliberately does NOT do:

- Does not implement Byzantine consensus. The broker's
  ``BEGIN IMMEDIATE`` single-file serialization is enough for the
  single-machine coherence scope; cross-host consensus is Phase 6+.
- Does not cache the deserialized snapshot aggressively. Each
  ``latest_snapshot()`` call re-reads the broker. For the Genesis
  Default tick cadence (10 s) and the typical read rate (one read per
  ``/drive`` or ``/sensorium`` request) this is well within SQLite-WAL's
  concurrent-read budget. If future profiling shows the re-read cost
  is material, a tiny `(snapshot, updated_at_ns)` cache lands under the
  same Protocol surface.
"""

from __future__ import annotations

import asyncio
import os
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Mapping

from orchestrator.sensorium import (
    Chronoception,
    DistressSignal,
    Interoception,
    Proprioception,
    SensoriumState,
)

from orchestrator.runtime.broker import Broker

if TYPE_CHECKING:
    from orchestrator.relay import Relay
    from orchestrator.supervisor import Supervisor


_DEFAULT_FOLLOWER_POLL_S = 0.25
"""Cadence at which a follower polls for leader promotion. Small
enough that failover completes in approximately ``leader_lease_s +
_DEFAULT_FOLLOWER_POLL_S``; large enough not to busy-wait the broker."""


def deserialize_sensorium_state(payload: Mapping[str, Any]) -> SensoriumState:
    """Reconstruct a :class:`SensoriumState` from :meth:`SensoriumState.to_dict`
    output. Used by the follower shell when the broker returns a published
    snapshot.

    The round-trip preserves the five top-level slots exactly. Distress
    ``source`` is the literal string the leader wrote; the frozen dataclass
    does not validate the string beyond type, so any payload that a leader
    built via a real tick round-trips losslessly.
    """
    inter = payload["interoception"]
    chrono = payload["chronoception"]
    proprio = payload["proprioception"]
    distress = payload["distress"]
    return SensoriumState(
        interoception=Interoception(
            survival_pressure=float(inter["survival_pressure"]),
            treasury_stress=float(inter["treasury_stress"]),
            cost_pressure=float(inter["cost_pressure"]),
            as_of_utc_ns=int(inter["as_of_utc_ns"]),
        ),
        chronoception=Chronoception(
            as_of_utc_ns=int(chrono["as_of_utc_ns"]),
            checkpoint_staleness_s=float(chrono["checkpoint_staleness_s"]),
            time_in_degraded_mode_s=float(chrono["time_in_degraded_mode_s"]),
            monotonic_drift_ns=int(chrono["monotonic_drift_ns"]),
        ),
        proprioception=Proprioception(
            as_of_utc_ns=int(proprio["as_of_utc_ns"]),
            relay_healthy=bool(proprio["relay_healthy"]),
            arbiter_healthy=bool(proprio["arbiter_healthy"]),
            watchdog_fires_recent=int(proprio["watchdog_fires_recent"]),
        ),
        distress=DistressSignal(
            text_distress_score=float(distress["text_distress_score"]),
            source=str(distress["source"]),
            as_of_utc_ns=int(distress["as_of_utc_ns"]),
        ),
        as_of_utc_ns=int(payload["as_of_utc_ns"]),
    )


class BrokerSupervisorShell:
    """One worker's broker-mediated Supervisor lifecycle.

    Construct at lifespan startup. Call :meth:`initial_seed` once
    synchronously (it attempts leader acquisition and, if successful,
    runs a pre-seed tick — mirroring the single-worker
    ``supervisor.tick_once()`` pre-seed). Then schedule
    :meth:`run` as an asyncio task and store the returned task on
    ``app.state.supervisor_task``. Call :meth:`stop` on shutdown.

    Thread-safety: :meth:`latest_snapshot` is safe to call from any
    thread. All other methods run on the lifespan's asyncio loop.
    """

    def __init__(
        self,
        *,
        broker: Broker,
        worker_id: str,
        leader_renew_s: float,
        supervisor_factory: Callable[..., "Supervisor"],
        sensorium_ledger_path: Path | None,
        tick_cadence_s: float,
        relay: "Relay",
        follower_poll_s: float = _DEFAULT_FOLLOWER_POLL_S,
        presence_bus: Any | None = None,
        signal_bus: Any | None = None,
        receptor_registry: Any | None = None,
    ) -> None:
        if not worker_id:
            raise ValueError("worker_id must be non-empty")
        if leader_renew_s <= 0:
            raise ValueError("leader_renew_s must be > 0")
        if follower_poll_s <= 0:
            raise ValueError("follower_poll_s must be > 0")
        self._broker = broker
        self._worker_id = worker_id
        self._leader_renew_s = float(leader_renew_s)
        self._follower_poll_s = float(follower_poll_s)
        self._supervisor_factory = supervisor_factory
        self._sensorium_ledger_path = sensorium_ledger_path
        self._tick_cadence_s = float(tick_cadence_s)
        self._relay = relay
        self._presence_bus = presence_bus
        self._signal_bus = signal_bus
        self._receptor_registry = receptor_registry

        self._stop_event = threading.Event()
        self._role_lock = threading.Lock()
        self._leader_supervisor: Supervisor | None = None
        self._role: str = "follower"  # "leader" | "follower"

    # ----- Public surface that mirrors Supervisor -------------------------

    @property
    def worker_id(self) -> str:
        return self._worker_id

    @property
    def role(self) -> str:
        """Current dynamic role: ``"leader"`` or ``"follower"``. Safe to
        read from any thread."""
        with self._role_lock:
            return self._role

    @property
    def _current_supervisor(self) -> "Supervisor | None":
        with self._role_lock:
            return self._leader_supervisor

    def latest_snapshot(self) -> SensoriumState | None:
        """Return the most recent :class:`SensoriumState`, or ``None``.

        As leader: returns the local Supervisor's snapshot.
        As follower: reads the broker's published snapshot and
        deserializes it. A follower that has never observed a leader-
        published snapshot returns ``None`` (mirroring the pre-tick
        Supervisor posture).
        """
        sup = self._current_supervisor
        if sup is not None:
            return sup.latest_snapshot()
        blob = self._broker.latest_snapshot()
        if blob is None:
            return None
        try:
            return deserialize_sensorium_state(blob)
        except (KeyError, TypeError, ValueError):
            # A malformed broker row is operationally the same as "no
            # snapshot yet" from the follower's perspective. An
            # operator inspecting the broker can see the row shape;
            # the follower does not promote broker corruption into an
            # HTTP 500 for /sensorium.
            return None

    def tick_once(self) -> SensoriumState:
        """Delegate to the leader Supervisor. Raises if this shell is
        not currently leading — callers that need a snapshot while the
        shell is a follower should read :meth:`latest_snapshot`."""
        sup = self._current_supervisor
        if sup is None:
            raise RuntimeError(
                "BrokerSupervisorShell.tick_once called while follower; "
                "no local Supervisor to tick"
            )
        return sup.tick_once()

    def stop(self) -> None:
        """Signal :meth:`run` to exit at the next loop boundary."""
        self._stop_event.set()
        # Also stop the leader Supervisor if we are currently leading,
        # so its cooperative stop signal drains without waiting for
        # the shell loop to notice.
        with self._role_lock:
            if self._leader_supervisor is not None:
                self._leader_supervisor.stop()

    # ----- Synchronous startup seed ---------------------------------------

    def initial_seed(self) -> None:
        """One-shot synchronous startup: attempt leader acquisition and,
        if successful, run a pre-seed Supervisor tick so
        :meth:`latest_snapshot` is non-``None`` before the first request.

        If this worker does not win the initial election, ``latest_snapshot``
        may return ``None`` until the leader publishes its first tick; the
        follower's role in this window is to serve reads from the broker
        (which :meth:`latest_snapshot` already handles).
        """
        won = self._broker.try_acquire_leader(self._worker_id, time.time_ns())
        if won:
            supervisor = self._build_leader_supervisor()
            supervisor.tick_once()
            with self._role_lock:
                self._leader_supervisor = supervisor
                self._role = "leader"

    # ----- Async run loop --------------------------------------------------

    async def run(self) -> None:
        """The shell's main loop. Runs until :meth:`stop` is called.

        Two modes, a dynamic role flip between them:

        - **Leader.** Run the local Supervisor's tick loop and renew
          the broker lease on ``leader_renew_s`` cadence. If renewal
          fails, demote to follower.
        - **Follower.** Poll for promotion on ``follower_poll_s``
          cadence. When ``try_acquire_leader`` succeeds, promote.
        """
        try:
            while not self._stop_event.is_set():
                if self.role == "leader":
                    await self._run_as_leader()
                else:
                    await self._run_as_follower_once()
        finally:
            self._stop_event.set()
            with self._role_lock:
                if self._leader_supervisor is not None:
                    self._leader_supervisor.stop()

    async def _run_as_leader(self) -> None:
        """Start a leader Supervisor task + renewal loop; run until
        demoted or stopped. On demotion the Supervisor task is
        cancelled and control returns to :meth:`run` which will then
        enter follower mode."""
        supervisor = self._current_supervisor
        if supervisor is None:
            # Pre-seed was skipped (e.g. worker acquired leadership
            # mid-run). Build and pre-seed here.
            supervisor = self._build_leader_supervisor()
            with self._role_lock:
                self._leader_supervisor = supervisor
            # Pre-seed so follower workers are not waiting on our
            # first tick's broker publish.
            try:
                supervisor.tick_once()
            except Exception:
                # A first-tick failure (disk full, permission) is the
                # same structural condition that breaks the single-
                # worker posture; let it propagate after we drop the
                # lease so a replacement can try.
                with self._role_lock:
                    self._leader_supervisor = None
                    self._role = "follower"
                raise

        supervisor_task = asyncio.create_task(
            supervisor.run(),
            name=f"xion-supervisor-run[{self._worker_id}]",
        )
        try:
            while not self._stop_event.is_set():
                # Sleep the renew cadence, then try to renew.
                try:
                    await asyncio.wait_for(
                        self._await_stop_event(),
                        timeout=self._leader_renew_s,
                    )
                    break  # stop_event fired
                except asyncio.TimeoutError:
                    pass

                still_leader = self._broker.renew_leader(
                    self._worker_id, time.time_ns()
                )
                if not still_leader:
                    # Demote: cancel the Supervisor, drop to follower.
                    break
        finally:
            supervisor.stop()
            if not supervisor_task.done():
                try:
                    await asyncio.wait_for(
                        supervisor_task,
                        timeout=max(1.0, 2.0 * self._tick_cadence_s),
                    )
                except asyncio.TimeoutError:
                    supervisor_task.cancel()
                    try:
                        await supervisor_task
                    except (asyncio.CancelledError, Exception):
                        # Cancellation or a terminal error in a
                        # cancelled Supervisor is fine at this point.
                        pass
            with self._role_lock:
                self._leader_supervisor = None
                if not self._stop_event.is_set():
                    self._role = "follower"

    async def _run_as_follower_once(self) -> None:
        """One pass of follower-mode polling."""
        try:
            await asyncio.wait_for(
                self._await_stop_event(),
                timeout=self._follower_poll_s,
            )
            return
        except asyncio.TimeoutError:
            pass
        if self._stop_event.is_set():
            return
        won = self._broker.try_acquire_leader(self._worker_id, time.time_ns())
        if won:
            with self._role_lock:
                self._role = "leader"

    async def _await_stop_event(self) -> None:
        """Yield until ``_stop_event`` is set. Mirrors Supervisor's
        implementation of the same pattern."""
        poll_interval_s = min(0.1, self._follower_poll_s / 4)
        while not self._stop_event.is_set():
            await asyncio.sleep(poll_interval_s)

    # ----- Helpers --------------------------------------------------------

    def _build_leader_supervisor(self) -> "Supervisor":
        """Construct a Supervisor wired with a broker-publish hook.

        Uses the factory passed at construction time so tests can
        inject a custom Supervisor subclass or a pre-configured instance.
        """
        return self._supervisor_factory(
            relay=self._relay,
            tick_cadence_s=self._tick_cadence_s,
            sensorium_ledger_path=self._sensorium_ledger_path,
            publish=lambda payload: self._broker.publish_snapshot(payload),
            presence_bus=self._presence_bus,
            signal_bus=self._signal_bus,
            receptor_registry=self._receptor_registry,
        )


def default_worker_id() -> str:
    """Build a worker id that is unique per-process on a single machine.

    Shape: ``<hostname>-<pid>``. ``hostname`` is the best-effort return
    of :func:`os.uname` / :func:`socket.gethostname`; ``pid`` is
    :func:`os.getpid`. An integrator with a custom multi-host topology
    can override at construction time; the default is sufficient for
    the Genesis single-machine deployment posture.
    """
    import socket

    try:
        host = socket.gethostname() or "unknown"
    except OSError:
        host = "unknown"
    return f"{host}-{os.getpid()}"


__all__ = [
    "BrokerSupervisorShell",
    "deserialize_sensorium_state",
    "default_worker_id",
]
