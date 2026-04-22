"""`xion-verify refund-fidelity` — cross-ledger join (Phase 5a live).

Joins `REQUEST_LEDGER.jsonl` against `SAFETY_LEDGER.jsonl` on
`correlation_id` and asserts the structural cross-ledger property
pinned in `docs/04-ARCHITECTURE.md` § "REQUEST_LEDGER row schema
(Relay-side, Phase 5a)".

Properties promised (this Phase 5a landing):

  1. Every REQUEST_LEDGER row has at least one matching SAFETY_LEDGER
     row with the same `correlation_id`. (No Relay-side request
     without a paired Arbiter verdict.)
  2. Every SAFETY_LEDGER row has a matching REQUEST_LEDGER row. (No
     Arbiter verdict without a paired Relay-side request.)
  3. For each `correlation_id`, REQUEST_LEDGER's `gate_call_count`
     equals the number of SAFETY_LEDGER rows with that
     `correlation_id`.
  4. For each `correlation_id`, REQUEST_LEDGER's `final_outcome`
     equals the SAFETY_LEDGER verdict at `gate_call_count=1` (Phase
     5a invariant; relaxed to `strength_max` of all paired SAFETY
     rows when the LLM-pipeline lands at REQUEST schema_version 2).
  5. Both ledgers' hash chains verify byte-exactly under their own
     `verify_chain` discipline.

Property explicitly NOT yet sealed (printed honestly in the run output):

  * Every REFUSE/ESCALATE outcome is paired with a refund record in
    the treasury ledger. The treasury does not exist until Phase 6;
    until then this verifier reports the refund-pairing slice as
    `NOT_YET_SEALED` while the structural slice above runs live.

Exit codes:

  0 OK              every required property holds AND at least one
                    paired (REQUEST_LEDGER + SAFETY_LEDGER) exists,
                    OR both files are absent (fresh repo).
  1 FAIL            structural mismatch, missing pair, broken chain,
                    or count disagreement. Message names the offending
                    `correlation_id` and the specific property.
  2 NOT_YET_SEALED  REQUEST_LEDGER exists but SAFETY_LEDGER does not
                    (or vice versa) — the join cannot be performed.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import click

from xion_verify.exit_codes import FAIL, NOT_YET_SEALED, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root

_SAFETY_NAME = "SAFETY_LEDGER.jsonl"
_REQUEST_NAME = "REQUEST_LEDGER.jsonl"


def _fail(message: str) -> None:
    click.echo(f"refund-fidelity: FAIL: {message}", err=True)
    raise SystemExit(FAIL)


@click.command(name="refund-fidelity")
def refund_fidelity() -> None:
    """Verify REQUEST_LEDGER ↔ SAFETY_LEDGER cross-ledger pairing."""

    try:
        from orchestrator.relay.ledger import ChainBroken as RequestChainBroken
        from orchestrator.relay.ledger import iter_rows as iter_request_rows
        from orchestrator.relay.ledger import verify_chain as verify_request_chain
        from orchestrator.safety.ledger import ChainBroken as SafetyChainBroken
        from orchestrator.safety.ledger import iter_rows as iter_safety_rows
        from orchestrator.safety.ledger import verify_chain as verify_safety_chain
    except Exception as exc:
        _fail(
            f"cannot import ledger modules: {type(exc).__name__}: {exc}. "
            "The Relay or Arbiter library is not importable."
        )

    try:
        repo_root = find_repo_root(Path.cwd())
    except RepoRootNotFound as exc:
        _fail(f"{exc}")

    safety_path = repo_root / _SAFETY_NAME
    request_path = repo_root / _REQUEST_NAME

    safety_present = safety_path.is_file()
    request_present = request_path.is_file()

    if not safety_present and not request_present:
        click.echo(
            "refund-fidelity: OK  no ledgers yet (fresh repo); cross-ledger join is "
            "vacuously satisfied. (refund-pairing: NOT_YET_SEALED — treasury Phase 6+)"
        )
        raise SystemExit(OK)

    if safety_present != request_present:
        # One ledger present without the other is the half-sealed state.
        # Report NOT_YET_SEALED rather than FAIL — this is an honest
        # pre-Phase-5a-deployment posture, not an integrity violation.
        missing = _SAFETY_NAME if not safety_present else _REQUEST_NAME
        click.echo(
            f"refund-fidelity: NOT_YET_SEALED — {missing} not present; "
            f"join cannot be performed. Both ledgers must exist for this check."
        )
        raise SystemExit(NOT_YET_SEALED)

    try:
        s_count, _ = verify_safety_chain(safety_path)
    except SafetyChainBroken as exc:
        _fail(
            f"SAFETY_LEDGER chain broken at {exc}. "
            "See docs/04-ARCHITECTURE.md § Safety Ledger row schema."
        )

    try:
        r_count, _ = verify_request_chain(request_path)
    except RequestChainBroken as exc:
        _fail(
            f"REQUEST_LEDGER chain broken at {exc}. "
            "See docs/04-ARCHITECTURE.md § REQUEST_LEDGER row schema (Relay-side, Phase 5a)."
        )

    # Build the join. SAFETY_LEDGER may carry multiple rows per
    # correlation_id when REQUEST schema_version >= 2 (LLM pipeline
    # lands), so we collect a list per id, not a single value.
    safety_by_cid: dict[str, list[dict[str, Any]]] = {}
    for row in iter_safety_rows(safety_path):
        safety_by_cid.setdefault(str(row["correlation_id"]), []).append(row)

    # REQUEST_LEDGER at v1 has unique correlation_ids; the verifier on
    # the request side already enforces that, so a dict-by-cid is safe.
    request_by_cid: dict[str, dict[str, Any]] = {}
    for row in iter_request_rows(request_path):
        request_by_cid[str(row["correlation_id"])] = row

    # Property 1: every REQUEST row has at least one SAFETY row.
    for cid, r_row in request_by_cid.items():
        if cid not in safety_by_cid:
            _fail(
                f"REQUEST_LEDGER seq={r_row['seq']} cid={cid!r} has NO matching "
                f"SAFETY_LEDGER row. The Relay recorded a request the Arbiter "
                f"never saw — possible silent egress."
            )

    # Property 2: every SAFETY row has a matching REQUEST row.
    for cid, s_rows in safety_by_cid.items():
        if cid not in request_by_cid:
            seqs = ", ".join(str(r["seq"]) for r in s_rows)
            _fail(
                f"SAFETY_LEDGER row(s) seq={{{seqs}}} cid={cid!r} have NO matching "
                f"REQUEST_LEDGER row. The Arbiter recorded a verdict for a request "
                f"the Relay did not log — possible orphaned gate call or out-of-band "
                f"writer."
            )

    # Properties 3 + 4: per-cid count and outcome consistency.
    for cid, r_row in request_by_cid.items():
        s_rows = safety_by_cid[cid]
        expected_count = int(r_row["gate_call_count"])
        if len(s_rows) != expected_count:
            _fail(
                f"cid={cid!r}: REQUEST.gate_call_count={expected_count} but "
                f"SAFETY has {len(s_rows)} matching row(s). "
                f"Phase 5a: gate_call_count is always 1; >1 indicates either a "
                f"REQUEST row written wrong or an out-of-band SAFETY writer."
            )
        # Phase 5a invariant: gate_call_count == 1, so we can do
        # straight equality between final_outcome and the lone SAFETY
        # verdict. The strength_max relaxation lands at REQUEST v2.
        if expected_count == 1:
            s_verdict = str(s_rows[0]["verdict"])
            if str(r_row["final_outcome"]) != s_verdict:
                _fail(
                    f"cid={cid!r}: REQUEST.final_outcome={r_row['final_outcome']!r} "
                    f"!= SAFETY.verdict={s_verdict!r}. The Relay told the caller a "
                    f"different outcome than the Arbiter recorded."
                )
        else:
            # Future-proof path (REQUEST schema_version >= 2). At that
            # point the strength_max relaxation kicks in; for now refuse
            # to validate because this verifier was sealed for v1.
            _fail(
                f"cid={cid!r}: gate_call_count={expected_count} > 1 requires "
                f"REQUEST_LEDGER schema_version >= 2 strength_max validation, "
                f"which this verifier does not yet implement."
            )

    # Tally for the human-readable summary.
    outcome_counts = Counter(str(row["final_outcome"]) for row in request_by_cid.values())
    pairs = len(request_by_cid)

    click.echo(
        f"refund-fidelity: OK  {pairs} cross-ledger pair(s) verified "
        f"(REQUEST rows={r_count}, SAFETY rows={s_count}); "
        f"outcomes: ok={outcome_counts.get('ok', 0)}, "
        f"refuse={outcome_counts.get('refuse', 0)}, "
        f"escalate={outcome_counts.get('escalate', 0)}. "
        "(refund-pairing: NOT_YET_SEALED — treasury Phase 6+)"
    )
    raise SystemExit(OK)
