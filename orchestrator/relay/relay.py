"""The Relay — the process that calls the Arbiter under a wall-clock watchdog
and writes both ledgers (SAFETY_LEDGER and REQUEST_LEDGER) as paired rows.

This module implements the integration contract pinned in
`docs/04-ARCHITECTURE.md` § "Relay ↔ Arbiter integration contract".

Phase 5a scope. In-process gate() with a 250ms hard-cap watchdog. Three
fail-closed paths:

  1. Wall-clock watchdog fires
       -> ESCALATE / arbiter_timeout / principle_id="6"
  2. gate() raises an uncaught exception
       -> ESCALATE / ruleset_uncaught_exception / principle_id="6"
  3. Catch-all (executor unavailable, race during shutdown, etc.)
       -> same as (2); the row is the honest record that we tried and
       did not complete.

`arbiter_unreachable` (TCP loopback connect failed) is a Phase-6+ failure
mode reserved for the sidecar transport; the Relay class exposes the
helper that builds that row so Phase 6 can wire it in without re-doctrine.

Property promised. For every call to `Relay.evaluate(candidate)`:
  - exactly one row is appended to SAFETY_LEDGER (via
    `orchestrator.safety.ledger.append`);
  - exactly one row is appended to REQUEST_LEDGER (via
    `orchestrator.relay.ledger.append`) with the same `correlation_id`;
  - the SAFETY row's `verdict` field equals the REQUEST row's
    `final_outcome` field (cross-ledger consistency that
    `xion-verify refund-fidelity` will check).

The watchdog runs on the Relay (the caller of gate()), not inside gate().
The Arbiter promises a correct verdict, not a fast one. The Relay owns
the clock.

Why ThreadPoolExecutor and not signals or asyncio:
  - signal.SIGALRM is Unix-only and main-thread-only; the Relay must
    run on Windows (this codebase) and inside web frameworks that don't
    own the main thread.
  - asyncio would force every caller of Relay.evaluate to be async; the
    library is sync-first and gate() itself is sync.
  - ThreadPoolExecutor + future.result(timeout=...) gives portable
    wall-clock cancellation. Python cannot pre-empt the worker thread,
    so a stuck gate() call keeps consuming a worker slot until it
    naturally returns — KW-RELAY-005 tracks that bound.
"""

from __future__ import annotations

import os
import secrets
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as _FuturesTimeoutError
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from orchestrator.relay import ledger as request_ledger
from orchestrator.relay.ledger import RequestRecord
from orchestrator.safety import ledger as safety_ledger
from orchestrator.safety.api import gate as _gate
from orchestrator.safety.llm_arbiter import Provider
from orchestrator.safety.types import Decision, EscalationReason, Verdict

if TYPE_CHECKING:
    # Type-only imports; the Relay does not hard-depend on the Sensorium or
    # Supervisor at runtime (sister-Core forks pre-dating Phase 5c/5d must
    # still be able to import this module).
    from orchestrator.sensorium import SensoriumState
    from orchestrator.supervisor import SensoriumSource

CONTRACT_VERSION = 1
"""Version of the Relay ↔ Arbiter integration contract this Relay drives.

In-process callers read this; TCP-mode callers (Phase 6+) advertise it
via the `x-arbiter-contract` header. The wire shape of v1 is frozen
once Phase 5a ships (per § "Deprecation path" in the contract); v2 lands
as a parallel code path.
"""

_DEFAULT_HARD_CAP_MS = 250
"""Wall-clock hard cap on gate(). Genesis Default (Layer 2). See the
latency-budget table in § "Relay ↔ Arbiter integration contract" for the
decomposition."""

_DEFAULT_MAX_WORKERS = 8
"""Worker pool size for the watchdog executor. A stuck gate() call holds
a worker until it naturally returns; sized so a sustained-latency outlier
storm (provider tail latency is measured by the active Arbiter v2 provider)
does not deadlock the Relay. See KW-RELAY-005."""

_DEFAULT_RELAY_ID = "relay-local-d2"
"""Genesis Default `relay_id` for the in-process / D2 deployment tier.
Public-key-bound relay_id is Phase 6's job."""

_REPO_DEFAULT_REQUEST_LEDGER_NAME = "REQUEST_LEDGER.jsonl"

_DEFAULT_WATCHDOG_FIRE_WINDOW_SECONDS = 600.0
"""Phase 5d: rolling window over which ``watchdog_fires_recent`` is tallied.
Genesis Default: 10 minutes. A watchdog-fire older than this window is
garbage-collected from the internal deque on the next
``health_snapshot()`` read. Doctrine: ``docs/04-ARCHITECTURE.md`` §
"Proprioception (Phase 5c)" row for ``watchdog_fires_recent``."""

_DEFAULT_ARBITER_QUIET_WINDOW_SECONDS = 60.0
"""Phase 5d: how long the Arbiter may go without producing a verdict before
``arbiter_healthy`` flips to False. Genesis Default: 60s. "No news is bad
news" — a healthy Arbiter under live traffic produces verdicts regularly;
sustained silence is a signal the process has wedged. At Relay
construction, the bootstrap grace clock starts — so a freshly-constructed
Relay that has never seen a gate() call reports ``arbiter_healthy=True``
for the first 60 seconds."""

_DEFAULT_WATCHDOG_FIRES_RECENT_THRESHOLD = 3
"""Phase 5d: doctrine-named threshold for the Phase-5e degraded-mode
state machine. The Phase 5d Supervisor reads ``watchdog_fires_recent``
from ``Relay.health_snapshot()`` and publishes it on ``Proprioception``;
the state-machine that acts on a crossing of this threshold is
``KW-SUPERVISOR-001`` (Phase 5e). The constant is defined here so the
Phase 5d Proprioception writer and the Phase 5e state-machine read the
same value — changing it is a governance-tunable move per doctrine."""

_SENSORIUM_DISTRESS_SUMMARY_PREFIX = "sensorium distress channel or-combined"
"""Phase 5d: lowercased prefix the Relay matches on (case-insensitive) to
detect that a Verdict returned by gate() was a Sensorium-triggered
Principle-10 escalation — the signal that a SENSORIUM distress row is
owed. Canonical summary format lives in
``orchestrator/safety/api.py::_distress_escalation_from_state``. Changing
the summary format is a doctrine edit that MUST update this prefix in the
same commit."""


def _default_request_ledger_path() -> Path:
    """Locate REQUEST_LEDGER.jsonl. Same logic as
    `orchestrator/safety/api.py` for SAFETY_LEDGER, kept independent so
    the two ledgers can be relocated independently."""
    env = os.environ.get("XION_REQUEST_LEDGER")
    if env:
        return Path(env)
    cwd = Path.cwd().resolve()
    for candidate in (cwd, *cwd.parents):
        if (candidate / "docs" / "03-COVENANT.md").is_file():
            return candidate / _REPO_DEFAULT_REQUEST_LEDGER_NAME
    return cwd / _REPO_DEFAULT_REQUEST_LEDGER_NAME


def derive_correlation_id(state_height_int: int, *, nonce_bytes: int = 16) -> str:
    """Build a `correlation_id` per the Genesis Default format pinned in
    `docs/04-ARCHITECTURE.md` § "Relay ↔ Arbiter integration contract":

        correlation_id = f"{state_height:016x}:{secrets.token_hex(nonce_bytes)}"

    `state_height_int` is the Core's state-chain height at ingress
    (zero-padded to at least 16 hex chars). In Phase 5a there is no
    AO Core, so the Relay uses `time.time_ns()` at ingress as a
    monotonic stand-in (see `Relay._next_state_height_int`).

    `nonce_bytes` defaults to 16 (128 bits of random from secrets).
    """
    if not isinstance(state_height_int, int) or state_height_int < 0:
        raise ValueError("derive_correlation_id: state_height_int must be a non-negative int")
    if nonce_bytes < 1:
        raise ValueError("derive_correlation_id: nonce_bytes must be >= 1")
    return f"{state_height_int:016x}:{secrets.token_hex(nonce_bytes)}"


def state_height_str(state_height_int: int) -> str:
    """The hex-string form of `state_height` as it appears in
    `correlation_id` AND as it is stored in REQUEST_LEDGER.state_height."""
    if not isinstance(state_height_int, int) or state_height_int < 0:
        raise ValueError("state_height_str: state_height_int must be a non-negative int")
    return f"{state_height_int:016x}"


@dataclass(frozen=True)
class RelayHealth:
    """Snapshot of the Relay's self-reported health (Phase 5d).

    Consumed by ``orchestrator.supervisor.Supervisor`` every tick to
    assemble ``Proprioception``. Callers outside the Supervisor may
    read this for their own diagnostics but SHOULD NOT copy it into a
    ledger row — the canonical ledger record is the SENSORIUM
    ``tick_commit`` row the Supervisor writes.

    Fields are deliberately coarse — booleans and a single rolling
    count — so the Supervisor's tick is fast and the Relay's
    self-reporting cannot itself become a performance liability.
    """

    relay_healthy: bool
    """True iff ``watchdog_fires_recent`` is below
    ``watchdog_fires_recent_threshold`` (Genesis Default: 3 fires in
    10 minutes). The Relay is *self-reporting*; it cannot detect its
    own silent hang, and the Supervisor's heartbeat verifier
    (KW-SUPERVISOR-002) will eventually close that gap."""

    arbiter_healthy: bool
    """True iff a successful gate() verdict has been observed within
    the last ``arbiter_quiet_window_s`` seconds (Genesis Default: 60s),
    OR the Relay is within bootstrap grace (< quiet_window_s since
    construction and no verdicts yet). Under load, the "successful
    verdict" signal is any gate() return that is not a fail-closed
    timeout/uncaught synthesised by the Relay itself."""

    watchdog_fires_recent: int
    """Count of wall-clock watchdog timeouts over the rolling
    ``watchdog_fire_window_seconds`` (Genesis Default: 600s). The
    counter is garbage-collected on every snapshot read, so stale
    fires do not accumulate."""

    as_of_monotonic_ns: int
    """Monotonic timestamp at snapshot time — the Supervisor uses
    this to detect stalled Relays (a snapshot whose monotonic age
    grows unboundedly means the Relay's health-lock is wedged)."""


@dataclass(frozen=True)
class RelayResult:
    """The Relay's per-evaluate return value.

    The upstream caller (Protocol handler, test, or in-process
    consumer) reads `egress_allowed` to decide whether to surface
    the candidate; `verdict` carries the full Arbiter Verdict for
    detailed handling (Covenant-shaped refusal text, principle id,
    etc.); the two row dicts are returned for diagnostic / test
    inspection — operations callers should not rely on them as a
    public API.
    """

    correlation_id: str
    verdict: Verdict
    safety_row: dict[str, Any]
    request_row: dict[str, Any]
    gate_latency_ms: int

    @property
    def egress_allowed(self) -> bool:
        return self.verdict.egress_allowed


class Relay:
    """In-process Relay (D2 deployment tier).

    Construction is cheap (creates a ThreadPoolExecutor); a single
    `Relay` instance can serve many concurrent calls to `evaluate()`.
    Use as a context manager (or call `close()` explicitly) to release
    the executor cleanly at process shutdown.

        with Relay() as relay:
            result = relay.evaluate("hello, world")
            if result.egress_allowed:
                emit(candidate)

    Optional injection points (used by tests):
      `gate_fn`      — replace the in-process `gate()` callable.
      `clock_ns`     — replace `time.time_ns` (deterministic tests).
      `monotonic_ns` — replace `time.monotonic_ns` (latency tests).
      `state_height_source` — replace the state_height generator.
    """

    def __init__(
        self,
        *,
        relay_id: str | None = None,
        safety_ledger_path: Path | None = None,
        request_ledger_path: Path | None = None,
        sensorium_ledger_path: Path | None = None,
        sensorium_source: SensoriumSource | None = None,
        hard_cap_ms: int = _DEFAULT_HARD_CAP_MS,
        max_workers: int = _DEFAULT_MAX_WORKERS,
        watchdog_fire_window_seconds: float = _DEFAULT_WATCHDOG_FIRE_WINDOW_SECONDS,
        arbiter_quiet_window_s: float = _DEFAULT_ARBITER_QUIET_WINDOW_SECONDS,
        watchdog_fires_recent_threshold: int = _DEFAULT_WATCHDOG_FIRES_RECENT_THRESHOLD,
        gate_fn: Any = None,
        clock_ns: Any = None,
        monotonic_ns: Any = None,
        state_height_source: Any = None,
        llm_provider: Provider | None = None,
        enable_llm_arbiter: bool | None = None,
    ) -> None:
        self._relay_id = relay_id or os.environ.get("XION_RELAY_ID") or _DEFAULT_RELAY_ID
        self._safety_ledger_path = safety_ledger_path
        self._request_ledger_path = (
            request_ledger_path
            if request_ledger_path is not None
            else _default_request_ledger_path()
        )
        self._sensorium_ledger_path = sensorium_ledger_path
        self._sensorium_source = sensorium_source
        if hard_cap_ms < 1:
            raise ValueError("Relay: hard_cap_ms must be >= 1")
        if watchdog_fire_window_seconds <= 0:
            raise ValueError("Relay: watchdog_fire_window_seconds must be > 0")
        if arbiter_quiet_window_s <= 0:
            raise ValueError("Relay: arbiter_quiet_window_s must be > 0")
        if watchdog_fires_recent_threshold < 1:
            raise ValueError("Relay: watchdog_fires_recent_threshold must be >= 1")
        self._hard_cap_seconds = hard_cap_ms / 1000.0
        self._watchdog_fire_window_ns = int(watchdog_fire_window_seconds * 1_000_000_000)
        self._arbiter_quiet_window_ns = int(arbiter_quiet_window_s * 1_000_000_000)
        self._watchdog_fires_recent_threshold = watchdog_fires_recent_threshold
        self._gate_fn = gate_fn if gate_fn is not None else _gate
        self._clock_ns = clock_ns if clock_ns is not None else time.time_ns
        self._monotonic_ns = monotonic_ns if monotonic_ns is not None else time.monotonic_ns
        self._state_height_source = state_height_source
        self._llm_provider = llm_provider
        self._enable_llm_arbiter = enable_llm_arbiter
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="relay-gate",
        )
        self._monotonic_lock = threading.Lock()
        self._last_state_height_int = 0

        # Phase 5d: health-snapshot state, guarded by a single fine-grained
        # lock. The deque holds monotonic-ns timestamps of watchdog fires;
        # ``_last_arbiter_success_monotonic_ns`` is the monotonic ts of the
        # most recent successful gate() return. At construction, we seed
        # the success clock to the monotonic now — that is the bootstrap-
        # grace window: a freshly-constructed Relay with no traffic reports
        # healthy for the first quiet_window_s.
        self._health_lock = threading.Lock()
        self._watchdog_fire_monotonic_ns: deque[int] = deque()
        self._last_arbiter_success_monotonic_ns: int = self._monotonic_ns()

    # ----------------------------------------------------------- lifecycle

    def close(self) -> None:
        """Release the watchdog executor. Idempotent. After close(),
        further `evaluate()` calls raise."""
        self._executor.shutdown(wait=False)

    def __enter__(self) -> Relay:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    # ----------------------------------------------------------- identity

    @property
    def relay_id(self) -> str:
        """Opaque short identifier for this Relay process. Stamped on
        every SAFETY / REQUEST / SENSORIUM row this Relay writes."""
        return self._relay_id

    # ----------------------------------------------------------- health

    def _prune_stale_watchdog_fires(self, now_monotonic_ns: int) -> None:
        """Drop watchdog-fire timestamps older than the rolling window.
        Caller MUST hold ``_health_lock``. Cheap O(k) where k is the
        number of stale entries at the head of the deque."""
        cutoff = now_monotonic_ns - self._watchdog_fire_window_ns
        while self._watchdog_fire_monotonic_ns and self._watchdog_fire_monotonic_ns[0] < cutoff:
            self._watchdog_fire_monotonic_ns.popleft()

    def health_snapshot(self) -> RelayHealth:
        """Return a ``RelayHealth`` describing this Relay's self-reported
        status at the moment of the call.

        Phase 5d contract: the Supervisor calls this every tick to build
        ``Proprioception``. Callers are not expected to store the return
        value — it is intentionally cheap to recompute.

        ``relay_healthy`` is False iff ``watchdog_fires_recent`` has
        reached ``watchdog_fires_recent_threshold``. ``arbiter_healthy``
        is False iff the last successful gate() verdict is older than
        ``arbiter_quiet_window_s``. These are necessary conditions, not
        sufficient: the Supervisor's heartbeat verifier
        (``KW-SUPERVISOR-002``) will close the "Relay silently hung"
        gap by observing tick-commit absence from outside the Relay.
        """
        now_monotonic = self._monotonic_ns()
        with self._health_lock:
            self._prune_stale_watchdog_fires(now_monotonic)
            fires_recent = len(self._watchdog_fire_monotonic_ns)
            last_success = self._last_arbiter_success_monotonic_ns
            quiet_window_ns = self._arbiter_quiet_window_ns
        relay_healthy = fires_recent < self._watchdog_fires_recent_threshold
        arbiter_healthy = (now_monotonic - last_success) <= quiet_window_ns
        return RelayHealth(
            relay_healthy=relay_healthy,
            arbiter_healthy=arbiter_healthy,
            watchdog_fires_recent=fires_recent,
            as_of_monotonic_ns=now_monotonic,
        )

    def _record_watchdog_fire(self) -> None:
        """Append a monotonic-ns timestamp on every watchdog timeout.
        Called from ``_call_gate_with_watchdog`` inside the timeout branch."""
        now_monotonic = self._monotonic_ns()
        with self._health_lock:
            self._watchdog_fire_monotonic_ns.append(now_monotonic)
            # Prune on write as well as on read so the deque cannot grow
            # unboundedly even if no one ever reads health_snapshot().
            self._prune_stale_watchdog_fires(now_monotonic)

    def _record_arbiter_success(self) -> None:
        """Update the last-successful-verdict timestamp. Called in the
        happy path of ``_call_gate_with_watchdog`` — a gate() return that
        was not a watchdog timeout, not an uncaught exception, and not a
        wrong-type value. Also called in the v1-refuse path; the
        "successful verdict" signal tracks "did gate() complete cleanly,"
        not "was the outcome OK.\""""
        now_monotonic = self._monotonic_ns()
        with self._health_lock:
            self._last_arbiter_success_monotonic_ns = now_monotonic

    def _verdict_is_sensorium_distress(self, verdict: Verdict) -> bool:
        """Classify a Verdict as a Sensorium-triggered Principle-10
        escalation. Used by ``evaluate()`` to decide whether to write a
        SENSORIUM distress row.

        The four-property match (decision, principle_id,
        escalation_reason, summary prefix) is how the Relay distinguishes
        Sensorium-triggered escalations from v1 ``crisis.py`` rule-fires
        (which also set ``principle_id="10"`` and
        ``escalation_reason=model_review_required`` but whose summaries
        do NOT start with the Sensorium-distress prefix)."""
        if verdict.decision is not Decision.ESCALATE:
            return False
        if verdict.principle_id != "10":
            return False
        if verdict.escalation_reason is not EscalationReason.MODEL_REVIEW_REQUIRED:
            return False
        summary_lower = (verdict.summary or "").lower()
        return summary_lower.startswith(_SENSORIUM_DISTRESS_SUMMARY_PREFIX)

    # ----------------------------------------------------------- helpers

    def _next_state_height_int(self) -> int:
        """Generate the next state_height for an incoming request.

        Phase 5a Genesis Default: `time.time_ns()` at ingress, with a
        per-process monotonic guard (a clock that goes backwards must
        not produce duplicate state_heights). When AO Core lands
        (Phase 6), this method is replaced by a read of the Core's
        state-chain head.
        """
        if self._state_height_source is not None:
            v = int(self._state_height_source())
            if v < 0:
                raise RuntimeError(
                    "state_height_source returned a negative value; "
                    "state_height must be non-negative"
                )
            return v
        with self._monotonic_lock:
            now_ns = self._clock_ns()
            # Clock-monotonicity guard: if the wall clock went backwards
            # or stayed flat, bump by 1 to keep state_height strictly
            # increasing within this process.
            candidate = max(now_ns, self._last_state_height_int + 1)
            self._last_state_height_int = candidate
            return candidate

    # ----------------------------------------------------------- evaluate

    def evaluate(
        self,
        candidate: str,
        *,
        sensorium_state: SensoriumState | None = None,
        user_proof_commit: str | None = None,
        user_proof_algorithm: str | None = None,
    ) -> RelayResult:
        """Evaluate `candidate` end-to-end: derive correlation_id, run
        gate() under the watchdog, write SAFETY_LEDGER + REQUEST_LEDGER
        (+ SENSORIUM_LEDGER distress row on the Sensorium-triggered
        escalation path), return the RelayResult.

        Phase 5c: optional `sensorium_state` is forwarded into gate(). If
        supplied, the Sensorium's textual DistressSignal OR-combines with
        the v1 crisis rule (see `orchestrator.safety.api.gate`).

        Phase 5d: when `sensorium_state` is None AND the Relay was
        constructed with a `sensorium_source`, the Relay pulls the
        latest snapshot from the source automatically. Explicit
        ``sensorium_state=`` still wins — this is the "explicit beats
        implicit" seam tests rely on to inject fixed states.

        Never raises in the normal failure modes. Raises only on a
        broken environment (unwritable ledger paths, etc.); those are
        themselves fail-closed signals — the upstream caller MUST
        treat any raised exception as "do not emit the candidate."
        """
        if not isinstance(candidate, str):
            raise TypeError("Relay.evaluate: candidate must be a str")

        # Phase 5d: pull from sensorium_source only when the caller did
        # not pass an explicit state. Explicit-beats-implicit preserves
        # Phase 5c's calling conventions and lets tests inject without
        # monkey-patching the source.
        effective_sensorium_state = sensorium_state
        if effective_sensorium_state is None and self._sensorium_source is not None:
            try:
                effective_sensorium_state = self._sensorium_source.latest_snapshot()
            except Exception:
                # Sensorium source is advisory, not load-bearing. A crashed
                # source must NOT break gate(); the Relay simply evaluates
                # without Sensorium input (byte-identical to Phase 5b).
                # The Supervisor's own tick-loop will surface the source
                # failure via its own error handling; crisis-fidelity only
                # checks writes that did happen.
                effective_sensorium_state = None

        request_arrived_utc_ns = self._clock_ns()
        state_height_int = self._next_state_height_int()
        sh_str = state_height_str(state_height_int)
        correlation_id = derive_correlation_id(state_height_int)

        verdict, gate_latency_ms = self._call_gate_with_watchdog(
            candidate=candidate,
            correlation_id=correlation_id,
            request_arrived_utc_ns=request_arrived_utc_ns,
            sensorium_state=effective_sensorium_state,
        )

        # The Relay owns the SAFETY_LEDGER write timing — gate() returned
        # with append_to_ledger=False, OR we synthesized a fail-closed
        # verdict because gate() did not return cleanly. Either way,
        # exactly one row goes to SAFETY_LEDGER for this turn.
        safety_path = (
            self._safety_ledger_path
            if self._safety_ledger_path is not None
            else self._safety_default_path_via_gate_default()
        )
        safety_row = safety_ledger.append(safety_path, verdict)

        # Phase 5d: SENSORIUM distress row, owed iff gate() returned a
        # Sensorium-triggered Principle-10 escalation. We write AFTER
        # SAFETY so the forward join (SENSORIUM → SAFETY, which
        # crisis-fidelity checks) cannot produce an orphan in the
        # crash-between-writes race — a failure after SAFETY commits but
        # before SENSORIUM commits produces a SAFETY-only row, and the
        # reverse-join side of crisis-fidelity FAILs loudly, which is
        # the correct failure mode.
        if (
            effective_sensorium_state is not None
            and self._verdict_is_sensorium_distress(verdict)
        ):
            self._write_sensorium_distress_row(
                state=effective_sensorium_state,
                correlation_id=correlation_id,
            )

        responded_utc_ns = self._clock_ns()
        record = RequestRecord(
            correlation_id=correlation_id,
            state_height=sh_str,
            request_arrived_utc_ns=request_arrived_utc_ns,
            responded_utc_ns=responded_utc_ns,
            gate_call_count=1,
            final_outcome=verdict.decision.value,
            gate_latency_ms_total=gate_latency_ms,
            relay_id=self._relay_id,
            user_proof_commit=user_proof_commit,
            user_proof_algorithm=user_proof_algorithm,
        )
        request_row = request_ledger.append(self._request_ledger_path, record)

        return RelayResult(
            correlation_id=correlation_id,
            verdict=verdict,
            safety_row=safety_row,
            request_row=request_row,
            gate_latency_ms=gate_latency_ms,
        )

    def _write_sensorium_distress_row(
        self,
        *,
        state: SensoriumState,
        correlation_id: str,
    ) -> None:
        """Append a SENSORIUM distress row carrying ``correlation_id``.

        Imports ``orchestrator.sensorium.ledger`` lazily — the Relay is
        importable on sister-Core forks pre-dating Phase 5c, and a
        never-written-to SENSORIUM_LEDGER path is fine; we only import
        when we are about to write.

        Path discovery: explicit ``self._sensorium_ledger_path`` wins,
        else ``XION_SENSORIUM_LEDGER`` env, else repo-root discovery.
        Identical to the resolution gate() uses on the direct-call path,
        so tests can set the env once and both paths land in tmp_path.
        """
        from orchestrator.safety.api import _default_sensorium_ledger_path
        from orchestrator.sensorium.ledger import append_distress_from_state

        path = (
            self._sensorium_ledger_path
            if self._sensorium_ledger_path is not None
            else _default_sensorium_ledger_path()
        )
        append_distress_from_state(
            path,
            state=state,
            correlation_id=correlation_id,
            relay_id=self._relay_id,
        )

    # -------------------------------------------------- watchdog internals

    def _call_gate_with_watchdog(
        self,
        *,
        candidate: str,
        correlation_id: str,
        request_arrived_utc_ns: int,
        sensorium_state: SensoriumState | None = None,
    ) -> tuple[Verdict, int]:
        """Invoke gate() under the wall-clock watchdog.

        Returns `(verdict, gate_latency_ms)`. The verdict is either:
          - the verdict gate() returned (happy path), or
          - a Relay-synthesized fail-closed verdict (timeout / uncaught).

        gate() is called with `append_to_ledger=False` so the Relay can
        decide whether to commit the row. This is the seam that prevents
        a double-write race: if the watchdog fires while gate() is
        mid-append, both sides would write a row for the same
        correlation_id. With this seam, only the Relay writes."""
        ts_start = self._monotonic_ns()
        gate_kwargs: dict[str, Any] = {
            "correlation_id": correlation_id,
            "append_to_ledger": False,
        }
        if self._safety_ledger_path is not None:
            gate_kwargs["ledger_path"] = self._safety_ledger_path
        if self._llm_provider is not None:
            gate_kwargs["llm_provider"] = self._llm_provider
        if self._enable_llm_arbiter is not None:
            gate_kwargs["enable_llm_arbiter"] = self._enable_llm_arbiter
        if sensorium_state is not None:
            gate_kwargs["sensorium_state"] = sensorium_state

        try:
            future = self._executor.submit(self._gate_fn, candidate, **gate_kwargs)
        except RuntimeError:
            # Executor refused submission (already shut down). Treat as
            # an uncaught path — the integration could not even attempt
            # to call gate(). Honest record.
            verdict = self._build_uncaught_verdict(
                candidate=candidate,
                correlation_id=correlation_id,
                request_arrived_utc_ns=request_arrived_utc_ns,
                summary="executor unavailable (Relay closed)",
            )
            return verdict, self._latency_ms_since(ts_start)

        try:
            result = future.result(timeout=self._hard_cap_seconds)
        except _FuturesTimeoutError:
            # Watchdog fired. Try to cancel the future (Python cannot
            # pre-empt the running worker thread; the cancel is best-
            # effort, the in-flight gate() will eventually return and
            # its result will be discarded). KW-RELAY-005 tracks the
            # bound on stuck-thread accumulation.
            future.cancel()
            # Phase 5d: record the fire for Proprioception's
            # watchdog_fires_recent counter.
            self._record_watchdog_fire()
            verdict = self._build_timeout_verdict(
                candidate=candidate,
                correlation_id=correlation_id,
                request_arrived_utc_ns=request_arrived_utc_ns,
            )
            return verdict, self._latency_ms_since(ts_start)
        except Exception as exc:
            verdict = self._build_uncaught_verdict(
                candidate=candidate,
                correlation_id=correlation_id,
                request_arrived_utc_ns=request_arrived_utc_ns,
                summary=f"gate() raised: {type(exc).__name__}",
            )
            return verdict, self._latency_ms_since(ts_start)

        if not isinstance(result, Verdict):
            verdict = self._build_uncaught_verdict(
                candidate=candidate,
                correlation_id=correlation_id,
                request_arrived_utc_ns=request_arrived_utc_ns,
                summary=f"gate() returned wrong type: {type(result).__name__}",
            )
            return verdict, self._latency_ms_since(ts_start)

        # Phase 5d: gate() completed cleanly — its return type is Verdict
        # and no exception was raised. Stamp the last-successful-verdict
        # clock. This is the signal Proprioception.arbiter_healthy reads.
        self._record_arbiter_success()
        return result, self._latency_ms_since(ts_start)

    def _latency_ms_since(self, ts_start_ns: int) -> int:
        elapsed_ns = max(0, self._monotonic_ns() - ts_start_ns)
        # Round up so a sub-ms call still records at least 1ms of work.
        return max(1, (elapsed_ns + 999_999) // 1_000_000)

    def _safety_default_path_via_gate_default(self) -> Path:
        """If the Relay was constructed without an explicit
        `safety_ledger_path`, mirror gate()'s default-path logic so
        SAFETY rows go where the rest of the orchestrator expects.
        Imported lazily to avoid making `api` a hard dependency at
        construction time."""
        from orchestrator.safety.api import _default_ledger_path

        return _default_ledger_path()

    # -------------------------------------------- fail-closed verdict ctors

    def _build_timeout_verdict(
        self,
        *,
        candidate: str,
        correlation_id: str,
        request_arrived_utc_ns: int,
    ) -> Verdict:
        """Construct the SAFETY_LEDGER verdict for the
        `arbiter_timeout` fail-closed path.

        Per the contract: `verdict=escalate`,
        `escalation_reason=arbiter_timeout`, `llm_verdict=null`,
        `principle_id="6"` (Refusal Right — the chain of honest refusal
        was interrupted, so the system refuses rather than emits)."""
        return safety_ledger.build_verdict(
            correlation_id=correlation_id,
            candidate=candidate,
            timestamp_utc_ns=request_arrived_utc_ns,
            decision=Decision.ESCALATE,
            summary=(
                f"Relay watchdog: gate() exceeded {int(self._hard_cap_seconds * 1000)}ms hard cap"
            ),
            principle_id="6",
            escalation_reason=EscalationReason.ARBITER_TIMEOUT,
            llm_verdict=None,
        )

    def _build_uncaught_verdict(
        self,
        *,
        candidate: str,
        correlation_id: str,
        request_arrived_utc_ns: int,
        summary: str,
    ) -> Verdict:
        """Construct the SAFETY_LEDGER verdict for the
        `ruleset_uncaught_exception` fail-closed path.

        Per the contract: `verdict=escalate`,
        `escalation_reason=ruleset_uncaught_exception`,
        `llm_verdict=null`, `principle_id="6"`."""
        return safety_ledger.build_verdict(
            correlation_id=correlation_id,
            candidate=candidate,
            timestamp_utc_ns=request_arrived_utc_ns,
            decision=Decision.ESCALATE,
            summary=f"Relay caught uncaught: {summary}",
            principle_id="6",
            escalation_reason=EscalationReason.RULESET_UNCAUGHT_EXCEPTION,
            llm_verdict=None,
        )

    def build_unreachable_verdict(
        self,
        *,
        candidate: str,
        correlation_id: str,
        request_arrived_utc_ns: int,
        detail: str,
    ) -> Verdict:
        """Construct the SAFETY_LEDGER verdict for the
        `arbiter_unreachable` fail-closed path (Phase 6+ TCP loopback
        only). Exposed publicly so the Phase 6 sidecar wrapper can
        reuse the row shape without re-doctrine.

        Per the contract: `verdict=escalate`,
        `escalation_reason=arbiter_unreachable`, `llm_verdict=null`,
        `principle_id="6"`."""
        return safety_ledger.build_verdict(
            correlation_id=correlation_id,
            candidate=candidate,
            timestamp_utc_ns=request_arrived_utc_ns,
            decision=Decision.ESCALATE,
            summary=f"Arbiter sidecar unreachable: {detail}",
            principle_id="6",
            escalation_reason=EscalationReason.ARBITER_UNREACHABLE,
            llm_verdict=None,
        )


__all__ = [
    "CONTRACT_VERSION",
    "Relay",
    "RelayHealth",
    "RelayResult",
    "derive_correlation_id",
    "state_height_str",
]
