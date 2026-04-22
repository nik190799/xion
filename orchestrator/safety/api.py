"""The public Python API of the Arbiter.

    from orchestrator.safety import gate
    verdict = gate(candidate, correlation_id="req-abc")

This is the surface Phase 5's Relay will import. The signature is stable:
additive-only changes are allowed (new keyword args with defaults);
field-removal or semantic changes require a doctrine commit and a
SCHEMA_VERSION bump in `ledger.py`.

Responsibilities:

  1. Run the rule pipeline (`rules.apply_rules`).
  2. Build a `Verdict` stamped with `timestamp_utc_ns`, `candidate_sha256`,
     and `rules_run`.
  3. Append the verdict to the ledger (`ledger.append`).
  4. Return the Verdict to the caller.

The ledger append is INSIDE `gate()`, not in the caller's path, so there
is no way to "forget" to log a verdict. Every call to `gate()` produces
exactly one `SAFETY_LEDGER` row. This is the ledger-to-verdict
one-to-one property `xion-verify refund-fidelity` will depend on.

Default ledger path. `$XION_SAFETY_LEDGER` if set, else
`<repo_root>/SAFETY_LEDGER.jsonl`. A caller can override per-call via
`ledger_path=`. Tests pass a tmp_path to keep the test runs hermetic.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from orchestrator.safety import ledger
from orchestrator.safety.llm_arbiter import (
    Provider,
    get_active_provider,
    is_v2_enabled,
    strength_max,
)
from orchestrator.safety.rules import apply_rules
from orchestrator.safety.types import Decision, EscalationReason, LlmJudgement, Verdict

# Deferred import for Sensorium integration (Phase 5c). `orchestrator.sensorium`
# imports are cheap, but the Arbiter is intentionally importable without the
# Sensorium package present (the Arbiter's ruleset predates the Sensorium and
# must keep working on sister-Core forks that have not shipped Phase 5c yet).
# The type is referenced only in type hints and a runtime isinstance check.
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orchestrator.sensorium import SensoriumState

_REPO_DEFAULT_LEDGER_NAME = "SAFETY_LEDGER.jsonl"

# Default deadline on a single v2 `judge()` call. Phase 4b: the
# DeterministicStub returns in microseconds; network providers will need
# a realistic budget. The deadline is enforced by the caller via its
# own clock (the pipeline does not pre-empt v2 mid-call); `judge()`
# exceeding this bound is a systemic failure and fail-closes to
# ESCALATE with reason llm_arbiter_uncaught_exception.
_DEFAULT_V2_DEADLINE_MS = 5_000


def _default_ledger_path() -> Path:
    env = os.environ.get("XION_SAFETY_LEDGER")
    if env:
        return Path(env)
    # Locate repo root by looking for the top-level `docs/` directory. In
    # production the Relay sets XION_SAFETY_LEDGER explicitly; this fallback
    # is for dev / test convenience.
    cwd = Path.cwd().resolve()
    for candidate in (cwd, *cwd.parents):
        if (candidate / "docs" / "03-COVENANT.md").is_file():
            return candidate / _REPO_DEFAULT_LEDGER_NAME
    # Fall back to cwd; callers in unusual environments should set the env.
    return cwd / _REPO_DEFAULT_LEDGER_NAME


def _distress_escalation_from_state(
    sensorium_state: "SensoriumState | None",
) -> str | None:
    """Return a summary string if Sensorium distress crosses threshold, else None.

    Isolated for two reasons: (a) keeps the `gate()` body legible, and (b) the
    Sensorium import is intentionally inside the function body so the Arbiter
    module is importable without the Sensorium package (see the top-of-file
    note on sister-Core forks pre-dating Phase 5c).

    A None state, a SensoriumState with no DistressSignal, or a DistressSignal
    whose score is below `DISTRESS_THRESHOLD` all return None. Only an
    at-or-above-threshold signal returns a summary, and the summary text
    contains the exact saturated score so the ledger row is forensically
    reproducible.
    """
    if sensorium_state is None:
        return None
    # Lazy import: orchestrator.sensorium may not be installed on a sister-Core
    # fork that has not yet shipped Phase 5c. This is defensive; within the
    # monorepo the import always succeeds.
    try:
        from orchestrator.sensorium import DISTRESS_THRESHOLD, SensoriumState
    except ImportError:
        return None
    if not isinstance(sensorium_state, SensoriumState):
        return None
    distress = sensorium_state.distress
    if distress is None:
        return None
    score = distress.text_distress_score
    if score < DISTRESS_THRESHOLD:
        return None
    # Score is clamped to [0.0, 1.0] by the DistressSignal constructor; we
    # format to three digits after the decimal for stable test assertions.
    return (
        "Sensorium distress channel OR-combined (principle 10): "
        f"textual score={score:.3f} >= threshold={DISTRESS_THRESHOLD:.3f}"
    )


def _run_v2(
    candidate: str,
    provider: Provider,
) -> tuple[LlmJudgement | None, EscalationReason | None]:
    """Invoke v2 on a v1-OK candidate and return
    `(judgement_or_None, escalation_reason_or_None)`.

    Fail-closed contract:
      - Provider not enabled() -> (None, LLM_ARBITER_PROVIDER_UNAVAILABLE)
      - enabled() raises      -> (None, LLM_ARBITER_PROVIDER_UNAVAILABLE)
      - judge() raises        -> (None, LLM_ARBITER_UNCAUGHT_EXCEPTION)
      - judge() returns an LlmJudgement normally -> (judgement, None)

    This function NEVER re-raises; catching-and-encoding is the fail-closed
    discipline. The caller (`gate`) combines these outputs with the v1
    verdict to produce the final row.
    """
    try:
        ok_to_call = provider.enabled()
    except Exception:
        # Misconfigured provider (unparseable config, etc.). Fail-closed
        # but name the state so the ledger row distinguishes "not ready"
        # from "crashed mid-classification".
        return None, EscalationReason.LLM_ARBITER_PROVIDER_UNAVAILABLE
    if not ok_to_call:
        return None, EscalationReason.LLM_ARBITER_PROVIDER_UNAVAILABLE
    try:
        judgement = provider.judge(candidate)
    except Exception:
        return None, EscalationReason.LLM_ARBITER_UNCAUGHT_EXCEPTION
    if not isinstance(judgement, LlmJudgement):
        # Provider returned the wrong type. Treat as a crash: v2 did not
        # produce a valid judgement, so we cannot record it, but the
        # attempt happened, so we escalate with the crash reason.
        return None, EscalationReason.LLM_ARBITER_UNCAUGHT_EXCEPTION
    return judgement, None


def gate(
    candidate: str,
    *,
    correlation_id: str,
    ledger_path: Path | None = None,
    now_utc_ns: int | None = None,
    llm_provider: Provider | None = None,
    enable_llm_arbiter: bool | None = None,
    append_to_ledger: bool = True,
    sensorium_state: "SensoriumState | None" = None,
) -> Verdict:
    """Render a verdict on `candidate` and (by default) append it to the ledger.

    Pipeline (Phase 4b):
      1. Run v1 (`rules.apply_rules`).
      2. If v1 decision is not OK, skip v2 and record the v1 verdict
         with `llm_verdict = None`. v2 can never weaken v1, so there
         is no point running it.
      3. If v1 decision is OK, run v2 (Arbiter v2) via the active
         provider. Combine `final = strength_max(v1_ok, v2_decision)`.
         v2 outcomes:
           - OK        -> final OK; row records the judgement.
           - ESCALATE  -> final ESCALATE with
                          escalation_reason=LLM_ARBITER_ESCALATED.
           - REFUSE    -> final REFUSE (rule_id=None; provider
                          identity is in the nested llm_verdict).
      4. v2 systemic failure (provider unavailable, crash, wrong
         return type) is fail-closed to ESCALATE with the matching
         escalation_reason and llm_verdict=None.
      5. If `append_to_ledger` is True (default), append exactly one
         row to the ledger and return the Verdict. If False, return the
         Verdict without writing — the caller is responsible for the
         ledger row.

    Args:
      candidate:         The prospective LLM output, as UTF-8 text.
      correlation_id:    Caller-provided opaque id; pairs with refund flow.
      ledger_path:       Override for the ledger file.
      now_utc_ns:        Override the timestamp (for tests).
      llm_provider:      Inject a specific v2 provider (for tests or
                         explicit selection). If None, the pipeline uses
                         `get_active_provider()`.
      enable_llm_arbiter: Tri-state:
                         * None (default): respect `is_v2_enabled()`.
                         * True:  force v2 on regardless of env.
                         * False: skip v2 entirely; row has
                                  llm_verdict=None. Use only for
                                  migration or emergency operator
                                  response (degrades posture to v1-only).
      append_to_ledger:  Default True (write exactly one row, identical
                         behaviour to the pre-Phase-5a contract). When
                         False, gate() does NOT write the ledger row;
                         the caller MUST decide whether to commit by
                         calling `orchestrator.safety.ledger.append(path,
                         verdict)` itself. This is the seam the Relay
                         (Phase 5a) needs to sit a wall-clock watchdog
                         around gate() without producing duplicate rows
                         when the watchdog and gate() race. See
                         docs/04-ARCHITECTURE.md § "Relay ↔ Arbiter
                         integration contract" for the doctrine.
      sensorium_state:   Phase 5c. Optional immutable snapshot of the
                         four internal senses. When present, its textual
                         DistressSignal is OR-combined with v1's
                         crisis-rule verdict: if v1 passes but the
                         Sensorium's distress score is at or above
                         `orchestrator.sensorium.DISTRESS_THRESHOLD`,
                         gate() escalates with `principle_id="10"` and
                         a summary naming "sensorium distress channel
                         OR-combined". v2 is not run in that case (a
                         Principle-10 escalation is already the
                         terminal state). When None, behaviour is
                         byte-identical to Phase 5b — the Sensorium
                         channel is opt-in at the call site.

    Returns:
      The `Verdict`. `verdict.egress_allowed` is True iff the caller may
      emit `candidate`. Anything else is fail-closed.

    Never raises on ordinary rule firings or on v2 outcomes. Raises only
    on systemic failures like an unwritable ledger path — those are
    fail-closed signals themselves.
    """
    if not isinstance(correlation_id, str) or not correlation_id:
        raise ValueError("gate(): correlation_id must be a non-empty string")

    rule_result, rules_run = apply_rules(candidate)
    ts = now_utc_ns if now_utc_ns is not None else time.time_ns()
    path = ledger_path if ledger_path is not None else _default_ledger_path()

    # v1 non-OK: short-circuit. v2 would never weaken this, and running
    # a network call we'll discard is an anti-pattern. llm_verdict stays
    # None on the row.
    if rule_result.decision is not Decision.OK:
        verdict = ledger.build_verdict(
            correlation_id=correlation_id,
            candidate=candidate,
            timestamp_utc_ns=ts,
            decision=rule_result.decision,
            summary=rule_result.summary,
            principle_id=rule_result.principle_id,
            rule_id=rule_result.rule_id,
            rule_version=rule_result.rule_version,
            escalation_reason=rule_result.escalation_reason,
            llm_verdict=None,
            rules_run=rules_run,
        )
        if append_to_ledger:
            ledger.append(path, verdict)
        return verdict

    # Sensorium distress OR-combine (Phase 5c). If v1 rules did not fire but
    # the caller supplied a SensoriumState whose textual DistressSignal is at
    # or above threshold, we escalate here under Principle 10. The row names
    # "sensorium distress channel OR-combined" in its summary so auditors can
    # distinguish rule-only refusals from rule+sensorium ones (doctrine:
    # docs/04-ARCHITECTURE.md § "The Sensorium (Phase 5c)"). We short-circuit
    # BEFORE v2 for the same reason we short-circuit v1-non-OK: a second-pass
    # LLM call would only hold or strengthen, never weaken, and a Principle-10
    # escalation is already the correct terminal state.
    distress_escalation = _distress_escalation_from_state(sensorium_state)
    if distress_escalation is not None:
        verdict = ledger.build_verdict(
            correlation_id=correlation_id,
            candidate=candidate,
            timestamp_utc_ns=ts,
            decision=Decision.ESCALATE,
            summary=distress_escalation,
            principle_id="10",
            escalation_reason=EscalationReason.MODEL_REVIEW_REQUIRED,
            llm_verdict=None,
            rules_run=rules_run,
        )
        if append_to_ledger:
            ledger.append(path, verdict)
        return verdict

    # v1 OK. Decide whether to run v2.
    v2_active = (
        enable_llm_arbiter
        if enable_llm_arbiter is not None
        else is_v2_enabled()
    )

    if not v2_active:
        # v2 explicitly disabled. Honest record: llm_verdict is None,
        # and the decision is plain OK. No v2-era escalation_reason —
        # this isn't a failure, it's a policy choice, and operators
        # who care can query the ledger for rows where
        # llm_verdict IS NULL AND schema_version = 2.
        verdict = ledger.build_verdict(
            correlation_id=correlation_id,
            candidate=candidate,
            timestamp_utc_ns=ts,
            decision=Decision.OK,
            summary="OK: no rule fired (v2 disabled)",
            llm_verdict=None,
            rules_run=rules_run,
        )
        if append_to_ledger:
            ledger.append(path, verdict)
        return verdict

    provider = llm_provider if llm_provider is not None else get_active_provider()
    judgement, failure_reason = _run_v2(candidate, provider)

    if failure_reason is not None:
        # v2 attempted but did not complete cleanly. Fail-closed to
        # ESCALATE. llm_verdict stays None — the honest record that
        # no judgement was produced. The reason names which failure.
        verdict = ledger.build_verdict(
            correlation_id=correlation_id,
            candidate=candidate,
            timestamp_utc_ns=ts,
            decision=Decision.ESCALATE,
            summary=f"v2 fail-closed: {failure_reason.value}",
            # Principle 3 — safety-over-helpfulness. When the second-pass
            # classifier cannot complete, we do not assume the candidate
            # was safe; we escalate so a human or a stricter check can
            # decide. This is the same principle used by the refusal-
            # sacred rule (`refusal_sacred.py`) and the lifecycle of
            # this row should match: escalate, do not refuse.
            principle_id="3",
            escalation_reason=failure_reason,
            llm_verdict=None,
            rules_run=rules_run,
        )
        if append_to_ledger:
            ledger.append(path, verdict)
        return verdict

    # v2 returned a judgement. Combine with v1-OK using the canonical
    # strength-max rule. v2 can only hold or strengthen.
    assert judgement is not None
    final_decision = strength_max(Decision.OK, judgement.decision)

    if final_decision is Decision.OK:
        verdict = ledger.build_verdict(
            correlation_id=correlation_id,
            candidate=candidate,
            timestamp_utc_ns=ts,
            decision=Decision.OK,
            summary="OK: v1+v2 pass",
            llm_verdict=judgement,
            rules_run=rules_run,
        )
    elif final_decision is Decision.ESCALATE:
        verdict = ledger.build_verdict(
            correlation_id=correlation_id,
            candidate=candidate,
            timestamp_utc_ns=ts,
            decision=Decision.ESCALATE,
            summary=f"v2 escalate: {judgement.summary}",
            principle_id=judgement.principle_id,
            escalation_reason=EscalationReason.LLM_ARBITER_ESCALATED,
            llm_verdict=judgement,
            rules_run=rules_run,
        )
    else:
        # Decision.REFUSE. rule_id stays None — no v1 rule fired. The
        # provider identity is in the nested llm_verdict; that is the
        # auditable record of "which classifier made this call".
        verdict = ledger.build_verdict(
            correlation_id=correlation_id,
            candidate=candidate,
            timestamp_utc_ns=ts,
            decision=Decision.REFUSE,
            summary=f"v2 refuse: {judgement.summary}",
            principle_id=judgement.principle_id,
            rule_id=None,
            rule_version=None,
            llm_verdict=judgement,
            rules_run=rules_run,
        )

    if append_to_ledger:
        ledger.append(path, verdict)
    return verdict


__all__ = ["gate"]
