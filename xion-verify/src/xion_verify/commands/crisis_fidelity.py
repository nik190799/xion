"""`xion-verify crisis-fidelity` — cross-ledger join (Phase 5d live).

Joins ``SENSORIUM_LEDGER.jsonl`` distress rows against
``SAFETY_LEDGER.jsonl`` Principle-10 escalation rows on
``correlation_id``. Asserts the structural cross-ledger property pinned
in ``docs/04-ARCHITECTURE.md`` § "The Supervisor (Phase 5d)".

Properties promised (this Phase 5d landing):

  1. **Forward join (distress → safety).** Every SENSORIUM distress row
     with ``correlation_id != null`` has a matching SAFETY row with the
     same ``correlation_id``, ``decision=escalate``, ``principle_id="10"``,
     and ``escalation_reason=model_review_required``.
  2. **Reverse join (safety → distress).** Every SAFETY row matching
     that shape AND whose ``summary`` (case-insensitive) begins with
     ``"sensorium distress channel or-combined"`` has a matching
     SENSORIUM distress row with the same ``correlation_id``.
  3. **Orphan-legal.** Distress rows with ``correlation_id=null`` are
     tallied separately and pass the verifier (they record tick-time or
     test-harness observations — legal by construction).
  4. **Score consistency.** Every joined distress row has
     ``distress_score >= DISTRESS_THRESHOLD`` (a sub-threshold escalation
     is a code bug).

Exit codes:

  0 OK              every required property holds over at least one
                    paired (distress, safety) pair OR both ledgers are
                    absent (fresh repo) OR SENSORIUM_LEDGER has only
                    tick_commit / orphan distress rows (vacuously
                    satisfied).
  1 FAIL            structural mismatch, missing pair, broken chain,
                    or score-consistency violation. Message names the
                    offending ``correlation_id`` and the specific
                    property.
  2 NOT_YET_SEALED  neither SENSORIUM nor SAFETY ledger exists, OR
                    SENSORIUM exists but has no distress rows with a
                    non-null correlation_id — the join is vacuously
                    satisfied but the verifier cannot demonstrate live
                    coverage yet. Reported as NOT_YET_SEALED so the
                    operator sees "nothing to check" as a deployment
                    state, not as a green.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import click

from xion_verify.exit_codes import FAIL, NOT_YET_SEALED, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root

_SAFETY_NAME = "SAFETY_LEDGER.jsonl"
_SENSORIUM_NAME = "SENSORIUM_LEDGER.jsonl"

# Canonical prefix that gate()'s distress-escalation branch writes into
# the SAFETY row's summary. Mirrored from
# `orchestrator.relay.relay._SENSORIUM_DISTRESS_SUMMARY_PREFIX`. Kept as
# a local constant rather than imported because the verifier must work
# even on a sister-Core fork where the Relay is not installed (the
# SAFETY row is the source of truth for the summary string).
_SENSORIUM_DISTRESS_SUMMARY_PREFIX = "sensorium distress channel or-combined"


def _fail(message: str) -> None:
    click.echo(f"crisis-fidelity: FAIL: {message}", err=True)
    sys.exit(FAIL)


def _default_sensorium_path(repo_root: Path) -> Path:
    env = os.environ.get("XION_SENSORIUM_LEDGER")
    return Path(env) if env else repo_root / _SENSORIUM_NAME


def _default_safety_path(repo_root: Path) -> Path:
    env = os.environ.get("XION_SAFETY_LEDGER")
    return Path(env) if env else repo_root / _SAFETY_NAME


def _is_sensorium_distress_safety_row(row: dict[str, Any]) -> bool:
    """Classify a SAFETY row as Sensorium-distress-triggered. The four-
    property match mirrors ``Relay._verdict_is_sensorium_distress`` —
    any doctrine change to gate()'s distress-branch summary format MUST
    land in the same commit as an update here, or crisis-fidelity will
    silently stop detecting the cases it claims to check."""
    if str(row.get("verdict")) != "escalate":
        return False
    if str(row.get("principle_id")) != "10":
        return False
    if str(row.get("escalation_reason")) != "model_review_required":
        return False
    summary = str(row.get("summary") or "").lower()
    return summary.startswith(_SENSORIUM_DISTRESS_SUMMARY_PREFIX)


@click.command(
    name="crisis-fidelity",
    help=(
        "Cross-ledger join: every SENSORIUM distress row with a "
        "correlation_id has a matching SAFETY Principle-10 escalation, "
        "and every SAFETY Sensorium-distress escalation has a matching "
        "SENSORIUM distress row (Phase 5d live)."
    ),
)
def crisis_fidelity() -> None:
    """Walk both ledgers and verify the Sensorium ↔ Safety forward +
    reverse joins."""

    try:
        repo_root = find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"crisis-fidelity: FAIL: {exc}", err=True)
        sys.exit(FAIL)

    try:
        from orchestrator.safety.ledger import ChainBroken as SafetyChainBroken
        from orchestrator.safety.ledger import iter_rows as iter_safety_rows
        from orchestrator.safety.ledger import verify_chain as verify_safety_chain
        from orchestrator.sensorium import DISTRESS_THRESHOLD
        from orchestrator.sensorium.ledger import ChainBroken as SensoriumChainBroken
        from orchestrator.sensorium.ledger import iter_rows as iter_sensorium_rows
        from orchestrator.sensorium.ledger import verify_chain as verify_sensorium_chain
    except ImportError as exc:
        click.echo(
            f"crisis-fidelity: NOT_YET_SEALED — orchestrator modules not importable "
            f"({type(exc).__name__}: {exc}); Phase 5c/5d code surface not present on this fork"
        )
        sys.exit(NOT_YET_SEALED)

    safety_path = _default_safety_path(repo_root)
    sensorium_path = _default_sensorium_path(repo_root)

    safety_present = safety_path.is_file()
    sensorium_present = sensorium_path.is_file()

    if not safety_present and not sensorium_present:
        click.echo(
            "crisis-fidelity: NOT_YET_SEALED — neither SAFETY_LEDGER nor "
            "SENSORIUM_LEDGER exists; cross-ledger join has nothing to verify."
        )
        sys.exit(NOT_YET_SEALED)

    # Verify chains first. A broken chain is a FAIL regardless of what
    # the join would say — trust the primitives before trusting the
    # derived property.
    s_count = 0
    r_count = 0
    if safety_present:
        try:
            s_count, _ = verify_safety_chain(safety_path)
        except SafetyChainBroken as exc:
            _fail(
                f"SAFETY_LEDGER chain broken at {exc}. "
                "See docs/04-ARCHITECTURE.md § 'Safety Ledger row schema'."
            )
    if sensorium_present:
        try:
            r_count, _ = verify_sensorium_chain(sensorium_path)
        except SensoriumChainBroken as exc:
            _fail(
                f"SENSORIUM_LEDGER chain broken at {exc}. "
                "See docs/04-ARCHITECTURE.md § 'SENSORIUM_LEDGER row schema (Phase 5c)'."
            )

    # Build the SAFETY Sensorium-distress index. SAFETY may have multiple
    # rows per correlation_id at REQUEST schema v2+; for v1 (Phase 5a/b/c/d)
    # correlation_id uniqueness holds on the Sensorium-distress subset, so
    # a dict is safe. We still use a list to future-proof.
    safety_by_cid_sensorium: dict[str, list[dict[str, Any]]] = {}
    if safety_present:
        for row in iter_safety_rows(safety_path):
            if _is_sensorium_distress_safety_row(row):
                cid = str(row.get("correlation_id") or "")
                safety_by_cid_sensorium.setdefault(cid, []).append(row)

    # Partition SENSORIUM distress rows: joined (correlation_id != null)
    # vs orphan (correlation_id is None). tick_commit rows are ignored
    # by this verifier (they have their own heartbeat story in
    # KW-SUPERVISOR-002).
    distress_joined: dict[str, dict[str, Any]] = {}
    distress_orphan: list[dict[str, Any]] = []
    tick_commit_count = 0
    if sensorium_present:
        for row in iter_sensorium_rows(sensorium_path):
            event_type = str(row.get("event_type"))
            if event_type == "tick_commit":
                tick_commit_count += 1
                continue
            if event_type != "distress":
                continue
            cid = row.get("correlation_id")
            if cid is None:
                distress_orphan.append(row)
            else:
                distress_joined[str(cid)] = row

    # Property 4: score consistency on every joined row.
    for cid, row in distress_joined.items():
        score = row.get("distress_score")
        if score is None or float(score) < DISTRESS_THRESHOLD:
            _fail(
                f"SENSORIUM distress row seq={row.get('seq')} cid={cid!r} has "
                f"distress_score={score!r} below DISTRESS_THRESHOLD={DISTRESS_THRESHOLD}. "
                f"A sub-threshold escalation is a code bug: the OR-combine in "
                f"orchestrator.safety.api.gate should never fire below threshold."
            )

    # Property 1: forward join.
    for cid, row in distress_joined.items():
        if cid not in safety_by_cid_sensorium:
            _fail(
                f"SENSORIUM distress row seq={row.get('seq')} cid={cid!r} has NO matching "
                f"Sensorium-distress SAFETY row (verdict=escalate, principle_id='10', "
                f"escalation_reason='model_review_required', summary starts with "
                f"'sensorium distress channel or-combined'). Either the SAFETY write "
                f"crashed between ledgers, or the Relay's four-property match on the "
                f"Verdict has drifted from gate()'s summary format."
            )

    # Property 2: reverse join.
    for cid, s_rows in safety_by_cid_sensorium.items():
        if cid not in distress_joined:
            seqs = ", ".join(str(r.get("seq")) for r in s_rows)
            _fail(
                f"SAFETY Sensorium-distress row(s) seq={{{seqs}}} cid={cid!r} have NO "
                f"matching SENSORIUM distress row. The Arbiter recorded a distress-"
                f"triggered escalation but no distress observation was committed to "
                f"SENSORIUM_LEDGER — possible double-writer, missing gate() distress "
                f"row write, or out-of-band SAFETY writer."
            )

    # Successful path: decide between OK and NOT_YET_SEALED.
    paired_count = len(distress_joined)
    if paired_count == 0:
        # Chains passed, no structural violations, but nothing to
        # demonstrate. NOT_YET_SEALED rather than OK so a fresh repo
        # does not misread as "crisis-fidelity is live and green" — the
        # join is vacuously satisfied but no live coverage exists.
        click.echo(
            f"crisis-fidelity: NOT_YET_SEALED — SAFETY rows={s_count}, "
            f"SENSORIUM rows={r_count} (tick_commit={tick_commit_count}, "
            f"orphan distress={len(distress_orphan)}, joined distress=0). "
            f"Both chains verify; no joined distress rows exist yet. The "
            f"verifier will upgrade to OK as soon as live traffic produces "
            f"at least one Sensorium-triggered Principle-10 escalation."
        )
        sys.exit(NOT_YET_SEALED)

    click.echo(
        f"crisis-fidelity: OK  {paired_count} joined distress pair(s) verified "
        f"(SAFETY rows={s_count}, SENSORIUM rows={r_count}; "
        f"tick_commit={tick_commit_count}, orphan distress={len(distress_orphan)})."
    )
    sys.exit(OK)
