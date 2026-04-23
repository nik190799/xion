"""`xion-verify refund-fidelity` — cross-ledger join (Phase 5a + 5g-vii).

Joins `REQUEST_LEDGER.jsonl` against `SAFETY_LEDGER.jsonl` on
`correlation_id` and asserts the structural cross-ledger properties
pinned in `docs/04-ARCHITECTURE.md` § "REQUEST_LEDGER row schema
(Relay-side, Phase 5a)" and `docs/26-INFERENCE-POLICY.md` § "Provider
fallback semantics (Phase 5g-vii)".

Properties promised (v1 gate-call rows, Phase 5a):

  1. Every REQUEST_LEDGER v1 row has at least one matching
     SAFETY_LEDGER row with the same `correlation_id`. (No Relay-side
     request without a paired Arbiter verdict.)
  2. Every SAFETY_LEDGER row has a matching REQUEST_LEDGER v1 row.
     (No Arbiter verdict without a paired Relay-side request.)
  3. For each v1 `correlation_id`, REQUEST_LEDGER's `gate_call_count`
     equals the number of SAFETY_LEDGER rows with that
     `correlation_id`.
  4. For each v1 `correlation_id`, REQUEST_LEDGER's `final_outcome`
     equals the SAFETY_LEDGER verdict at `gate_call_count=1`.
  5. Both ledgers' hash chains verify byte-exactly under their own
     `verify_chain` discipline.

Properties promised (v2 provider-attempt rows, Phase 5g-vii):

  6. The `failure_reason_class` enumeration in
     `orchestrator.inference_router.provider.FAILURE_REASON_CLASSES`
     equals the set pinned in
     `orchestrator.relay.ledger._ALLOWED_V2_FAILURE_REASON_CLASSES`.
     Drift is a doctrine violation (a typed class added to the
     provider hierarchy without a matching ledger pin, or vice versa).
  7. For every v2 row, the `correlation_id` matches a v1 row's
     `correlation_id` (the turn's ingress gate-call row). This keeps
     v2 attempt rows joinable into SAFETY_LEDGER via the existing v1
     join.
  8. Within each `chat_turn_id`:
       - `attempt_index` sequence is {0, 1, ..., N-1} (no gaps, no
         duplicates, starts at 0);
       - at most one row has `outcome="success"`;
       - if a success row exists, it is at the terminal
         `attempt_index` (= N-1) — i.e. the handler stopped trying
         providers after success;
       - rows with `outcome="failure"` carry a valid
         `failure_reason_class` in the P5 enum;
       - rows with `outcome="success"` carry
         `failure_reason_class=null`.

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
                    count disagreement, or v2 shape violation. Message
                    names the offending `correlation_id` or
                    `chat_turn_id` and the specific property.
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
        from orchestrator.inference_router.provider import (
            FAILURE_REASON_CLASSES as PROVIDER_FAILURE_REASON_CLASSES,
        )
        from orchestrator.relay.ledger import (
            _ALLOWED_V2_FAILURE_REASON_CLASSES as LEDGER_FAILURE_REASON_CLASSES,
        )
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

    # Property 6 (v2, Phase 5g-vii): doctrine ↔ code enumeration lock.
    # Drift between the provider-side typed classes and the ledger-side
    # v2 enum is a silent class addition without the required doctrine
    # amendment to docs/26-INFERENCE-POLICY.md § "Provider fallback
    # semantics" P5. We run this check BEFORE touching the ledger files
    # so a fresh repo (no ledger on disk) still verifies the structural
    # coupling.
    provider_set = set(PROVIDER_FAILURE_REASON_CLASSES)
    ledger_set = set(LEDGER_FAILURE_REASON_CLASSES)
    if provider_set != ledger_set:
        missing_from_ledger = provider_set - ledger_set
        missing_from_provider = ledger_set - provider_set
        parts: list[str] = []
        if missing_from_ledger:
            parts.append(
                f"in provider.FAILURE_REASON_CLASSES but not in "
                f"ledger._ALLOWED_V2_FAILURE_REASON_CLASSES: "
                f"{sorted(missing_from_ledger)}"
            )
        if missing_from_provider:
            parts.append(
                f"in ledger._ALLOWED_V2_FAILURE_REASON_CLASSES but not in "
                f"provider.FAILURE_REASON_CLASSES: "
                f"{sorted(missing_from_provider)}"
            )
        _fail(
            "P5 failure_reason_class drift: "
            + "; ".join(parts)
            + ". See docs/26-INFERENCE-POLICY.md § \"Provider fallback "
            "semantics\" P5 — adding a class requires a doctrine "
            "amendment, not a silent code edit."
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

    safety_by_cid: dict[str, list[dict[str, Any]]] = {}
    for row in iter_safety_rows(safety_path):
        safety_by_cid.setdefault(str(row["correlation_id"]), []).append(row)

    # Partition REQUEST rows by schema_version. v1 rows keep the unique-
    # correlation-id invariant; v2 rows may share correlation_id with a
    # v1 row (ingress correlation_id) but are uniquely keyed by
    # (chat_turn_id, attempt_index).
    request_v1_by_cid: dict[str, dict[str, Any]] = {}
    request_v2_rows: list[dict[str, Any]] = []
    for row in iter_request_rows(request_path):
        sv = int(row.get("schema_version", 1))
        if sv == 1:
            request_v1_by_cid[str(row["correlation_id"])] = row
        elif sv == 2:
            request_v2_rows.append(row)
        else:
            _fail(
                f"REQUEST_LEDGER seq={row.get('seq')} has unknown "
                f"schema_version={sv!r}. Refund-fidelity knows {{1, 2}}."
            )

    # Property 1: every REQUEST v1 row has at least one SAFETY row.
    for cid, r_row in request_v1_by_cid.items():
        if cid not in safety_by_cid:
            _fail(
                f"REQUEST_LEDGER v1 seq={r_row['seq']} cid={cid!r} has NO matching "
                f"SAFETY_LEDGER row. The Relay recorded a request the Arbiter "
                f"never saw — possible silent egress."
            )

    # Property 2: every SAFETY row has a matching REQUEST v1 row.
    for cid, s_rows in safety_by_cid.items():
        if cid not in request_v1_by_cid:
            seqs = ", ".join(str(r["seq"]) for r in s_rows)
            _fail(
                f"SAFETY_LEDGER row(s) seq={{{seqs}}} cid={cid!r} have NO matching "
                f"REQUEST_LEDGER v1 row. The Arbiter recorded a verdict for a request "
                f"the Relay did not log — possible orphaned gate call or out-of-band "
                f"writer."
            )

    # Properties 3 + 4: per-cid count and outcome consistency for v1 rows.
    for cid, r_row in request_v1_by_cid.items():
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
        # verdict. The strength_max relaxation lands at REQUEST v2
        # turn-aggregation (not yet implemented by this verifier; the
        # v2 rows this verifier DOES handle are provider-attempt rows,
        # not turn-aggregate rows).
        if expected_count == 1:
            s_verdict = str(s_rows[0]["verdict"])
            if str(r_row["final_outcome"]) != s_verdict:
                _fail(
                    f"cid={cid!r}: REQUEST.final_outcome={r_row['final_outcome']!r} "
                    f"!= SAFETY.verdict={s_verdict!r}. The Relay told the caller a "
                    f"different outcome than the Arbiter recorded."
                )
        else:
            _fail(
                f"cid={cid!r}: gate_call_count={expected_count} > 1 requires "
                f"REQUEST_LEDGER turn-aggregate validation, which this verifier "
                f"does not yet implement."
            )

    # Property 7 (v2): every v2 row's correlation_id must match a v1 row.
    for v2_row in request_v2_rows:
        cid = str(v2_row["correlation_id"])
        if cid not in request_v1_by_cid:
            _fail(
                f"REQUEST_LEDGER v2 seq={v2_row['seq']} "
                f"chat_turn_id={v2_row['chat_turn_id']!r} attempt_index="
                f"{v2_row['attempt_index']} cid={cid!r} has NO matching v1 "
                f"gate-call row. Multi-attempt provider rows MUST share the "
                f"turn's ingress correlation_id so the v1 join into "
                f"SAFETY_LEDGER still covers the turn."
            )

    # Property 8 (v2): per-chat_turn_id shape invariants.
    turns: dict[str, list[dict[str, Any]]] = {}
    for v2_row in request_v2_rows:
        turns.setdefault(str(v2_row["chat_turn_id"]), []).append(v2_row)

    v2_failure_counts: Counter[str] = Counter()
    v2_success_turns = 0
    v2_all_fail_turns = 0

    for tid, rows in turns.items():
        rows_sorted = sorted(rows, key=lambda r: int(r["attempt_index"]))
        indexes = [int(r["attempt_index"]) for r in rows_sorted]
        if indexes != list(range(len(indexes))):
            _fail(
                f"chat_turn_id={tid!r}: attempt_index sequence {indexes} is not "
                f"{{0, 1, ..., {len(indexes) - 1}}} — gaps, duplicates, or "
                f"missing 0. Every attempt must write exactly one v2 row."
            )
        success_rows = [r for r in rows_sorted if r["outcome"] == "success"]
        if len(success_rows) > 1:
            seqs = ", ".join(str(r["seq"]) for r in success_rows)
            _fail(
                f"chat_turn_id={tid!r}: {len(success_rows)} rows with "
                f"outcome='success' (seqs {seqs}). A turn can succeed at "
                f"most once; multiple successes indicate the fallback loop "
                f"did not short-circuit on success."
            )
        if success_rows:
            # The success row must be the terminal attempt — the chat
            # handler is required to stop trying providers after success.
            terminal = rows_sorted[-1]
            if terminal["outcome"] != "success":
                _fail(
                    f"chat_turn_id={tid!r}: outcome='success' at "
                    f"attempt_index={success_rows[0]['attempt_index']} is "
                    f"not the terminal attempt (terminal attempt_index="
                    f"{terminal['attempt_index']}, outcome="
                    f"{terminal['outcome']!r}). The handler attempted a "
                    f"further provider after success."
                )
            v2_success_turns += 1
        else:
            v2_all_fail_turns += 1

        for r in rows_sorted:
            outcome = r["outcome"]
            frc = r["failure_reason_class"]
            if outcome == "success":
                if frc is not None:
                    _fail(
                        f"chat_turn_id={tid!r} seq={r['seq']} attempt_index="
                        f"{r['attempt_index']}: outcome='success' but "
                        f"failure_reason_class={frc!r} (must be null)."
                    )
            else:
                if frc not in ledger_set:
                    _fail(
                        f"chat_turn_id={tid!r} seq={r['seq']} attempt_index="
                        f"{r['attempt_index']}: outcome='failure' with "
                        f"failure_reason_class={frc!r} not in the P5 enum "
                        f"{sorted(ledger_set)}."
                    )
                v2_failure_counts[str(frc)] += 1

    outcome_counts = Counter(
        str(row["final_outcome"]) for row in request_v1_by_cid.values()
    )
    pairs = len(request_v1_by_cid)

    v2_summary = ""
    if request_v2_rows:
        failures_fmt = (
            ", ".join(
                f"{k}={v}" for k, v in sorted(v2_failure_counts.items())
            )
            or "(none)"
        )
        v2_summary = (
            f"; v2 attempt rows: turns={len(turns)} "
            f"(success={v2_success_turns}, all_fail={v2_all_fail_turns}), "
            f"failure classes: {failures_fmt}"
        )

    click.echo(
        f"refund-fidelity: OK  {pairs} cross-ledger pair(s) verified "
        f"(REQUEST rows={r_count}, SAFETY rows={s_count}); "
        f"outcomes: ok={outcome_counts.get('ok', 0)}, "
        f"refuse={outcome_counts.get('refuse', 0)}, "
        f"escalate={outcome_counts.get('escalate', 0)}"
        f"{v2_summary}. "
        "(refund-pairing: NOT_YET_SEALED — treasury Phase 6+)"
    )
    raise SystemExit(OK)
