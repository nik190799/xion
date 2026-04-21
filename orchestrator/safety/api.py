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
from orchestrator.safety.rules import apply_rules
from orchestrator.safety.types import Decision, Verdict

_REPO_DEFAULT_LEDGER_NAME = "SAFETY_LEDGER.jsonl"


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


def gate(
    candidate: str,
    *,
    correlation_id: str,
    ledger_path: Path | None = None,
    now_utc_ns: int | None = None,
) -> Verdict:
    """Render a verdict on `candidate` and append it to the ledger.

    Args:
      candidate:      The prospective LLM output, as UTF-8 text. May be empty.
      correlation_id: Caller-provided opaque id; pairs with refund flow.
      ledger_path:    Override for the ledger file. Defaults to repo root or
                      $XION_SAFETY_LEDGER.
      now_utc_ns:     Override the timestamp (for tests). Defaults to
                      `time.time_ns()`.

    Returns:
      The `Verdict`. `verdict.egress_allowed` is `True` iff the caller may
      emit `candidate` to its caller. Anything else is fail-closed.

    Never raises on ordinary rule firings. Raises only on systemic failures
    (e.g., unwritable ledger path) — those are fail-closed signals themselves.
    """
    if not isinstance(correlation_id, str) or not correlation_id:
        raise ValueError("gate(): correlation_id must be a non-empty string")

    rule_result, rules_run = apply_rules(candidate)
    ts = now_utc_ns if now_utc_ns is not None else time.time_ns()
    path = ledger_path if ledger_path is not None else _default_ledger_path()

    if rule_result.decision is Decision.OK:
        verdict = ledger.build_verdict(
            correlation_id=correlation_id,
            candidate=candidate,
            timestamp_utc_ns=ts,
            decision=Decision.OK,
            summary="OK: no rule fired",
            rules_run=rules_run,
        )
    else:
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
            rules_run=rules_run,
        )

    ledger.append(path, verdict)
    return verdict


__all__ = ["gate"]
