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
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as _FuturesTimeoutError
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from orchestrator.relay import ledger as request_ledger
from orchestrator.relay.ledger import RequestRecord
from orchestrator.safety import ledger as safety_ledger
from orchestrator.safety.api import gate as _gate
from orchestrator.safety.llm_arbiter import Provider
from orchestrator.safety.types import Decision, EscalationReason, Verdict

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
storm (rare under the OpenAI Moderation provider's typical ~120ms p50)
does not deadlock the Relay. See KW-RELAY-005."""

_DEFAULT_RELAY_ID = "relay-local-d2"
"""Genesis Default `relay_id` for the in-process / D2 deployment tier.
Public-key-bound relay_id is Phase 6's job."""

_REPO_DEFAULT_REQUEST_LEDGER_NAME = "REQUEST_LEDGER.jsonl"


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
        hard_cap_ms: int = _DEFAULT_HARD_CAP_MS,
        max_workers: int = _DEFAULT_MAX_WORKERS,
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
        if hard_cap_ms < 1:
            raise ValueError("Relay: hard_cap_ms must be >= 1")
        self._hard_cap_seconds = hard_cap_ms / 1000.0
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

    # ----------------------------------------------------------- lifecycle

    def close(self) -> None:
        """Release the watchdog executor. Idempotent. After close(),
        further `evaluate()` calls raise."""
        self._executor.shutdown(wait=False)

    def __enter__(self) -> Relay:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

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

    def evaluate(self, candidate: str) -> RelayResult:
        """Evaluate `candidate` end-to-end: derive correlation_id, run
        gate() under the watchdog, write SAFETY_LEDGER + REQUEST_LEDGER,
        return the RelayResult.

        Never raises in the normal failure modes. Raises only on a
        broken environment (unwritable ledger paths, etc.); those are
        themselves fail-closed signals — the upstream caller MUST
        treat any raised exception as "do not emit the candidate."
        """
        if not isinstance(candidate, str):
            raise TypeError("Relay.evaluate: candidate must be a str")

        request_arrived_utc_ns = self._clock_ns()
        state_height_int = self._next_state_height_int()
        sh_str = state_height_str(state_height_int)
        correlation_id = derive_correlation_id(state_height_int)

        verdict, gate_latency_ms = self._call_gate_with_watchdog(
            candidate=candidate,
            correlation_id=correlation_id,
            request_arrived_utc_ns=request_arrived_utc_ns,
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
        )
        request_row = request_ledger.append(self._request_ledger_path, record)

        return RelayResult(
            correlation_id=correlation_id,
            verdict=verdict,
            safety_row=safety_row,
            request_row=request_row,
            gate_latency_ms=gate_latency_ms,
        )

    # -------------------------------------------------- watchdog internals

    def _call_gate_with_watchdog(
        self,
        *,
        candidate: str,
        correlation_id: str,
        request_arrived_utc_ns: int,
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
    "RelayResult",
    "derive_correlation_id",
    "state_height_str",
]
