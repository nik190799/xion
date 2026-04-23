"""``xion-verify refusal-is-free`` — SAFETY ↔ PAYMENT join (Phase 5g-iii live).

Joins ``SAFETY_LEDGER.jsonl`` against ``PAYMENT_LEDGER.jsonl`` on
``correlation_id`` and asserts the structural **Refusal-is-Free**
property pinned in ``genesis/COVENANT.md`` (addendum) and the
``PAYMENT_LEDGER`` schema in ``docs/schemas/ledger-payment.yaml``.

Properties promised (every chat turn that has executed since the
PAYMENT_LEDGER came live):

  A. Each ledger's hash chain verifies byte-exactly under its own
     ``verify_chain`` discipline. A tampered ledger invalidates every
     claim below.

  B. Money-shape (per PAYMENT row, structurally enforced by the
     writer + chain verifier but re-asserted here as a top-level
     Covenant property so operators/auditors see the specific row):

       * ``outcome=settled``  → ``settled_XION == committed_XION``
         and ``refund_XION == 0``.
       * ``outcome=refunded`` → ``refund_XION == committed_XION``
         and ``settled_XION == 0``.
       * ``posture=disabled`` → ``committed == settled == refund == 0``.

  C. Ingress / egress mirror — every PAYMENT row with
     ``refusal_stage`` in ``{"ingress", "egress"}`` has at least one
     matching SAFETY row (same ``correlation_id``) whose
     ``verdict=refuse``. Symmetrically, every SAFETY row with
     ``verdict=refuse`` that has ANY PAYMENT row for its
     ``correlation_id`` must map to at least one PAYMENT row with
     ``outcome=refunded``. The qualifier "that has any PAYMENT row"
     is deliberate: SAFETY rows predating the PAYMENT_LEDGER's
     first row are out of scope (no commitment ever existed for
     them; Refusal-is-Free is vacuously satisfied).

  D. Settled implies allowed — every PAYMENT row with
     ``outcome=settled`` has NO matching SAFETY row with
     ``verdict=refuse``. A ``settled`` payment for a refused turn
     would be a Covenant-tier integrity break.

Operational refusal stages (``no_floor``, ``provider_error``,
``provider_timeout``, ``empty_candidate``) are excluded from property
(C) on the ingress/egress side because they refuse the turn for
reasons the Arbiter never saw — the SAFETY_LEDGER carries only the
ingress ``verdict=ok`` row for these turns. Property (B) still applies:
the refund equals the commitment.

What this verifier does NOT do (with honest pointers):

  * It does not cross-walk to REQUEST_LEDGER. ``xion-verify
    refund-fidelity`` covers REQUEST ↔ SAFETY; the triple-join lands
    at Phase 6 when the treasury makes it audit-critical.
  * It does not check that the refund was actually paid back to the
    user (treasury Phase 6+). At 5g-iii, Refusal-is-Free is a
    *structural* property: the ledger records a refund commitment
    equal to the payment commitment; the treasury settlement
    verifier ships with the treasury.

Exit codes:

  0 OK              every required property holds, OR both ledgers
                    absent (fresh repo). Tallies printed.
  1 FAIL            structural mismatch, broken chain, money-shape
                    violation, or join contradiction. Message names
                    the offending ``correlation_id`` and the specific
                    property.
  2 NOT_YET_SEALED  one ledger present, the other absent — the join
                    cannot be performed. Returning OK in this
                    half-sealed state would silently claim a property
                    we cannot check.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import click

from xion_verify.exit_codes import FAIL, NOT_YET_SEALED, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root

_SAFETY_NAME = "SAFETY_LEDGER.jsonl"
_PAYMENT_NAME = "PAYMENT_LEDGER.jsonl"

_INGRESS_EGRESS: frozenset[str] = frozenset({"ingress", "egress"})


def _fail(message: str) -> None:
    click.echo(f"refusal-is-free: FAIL: {message}", err=True)
    raise SystemExit(FAIL)


@click.command(name="refusal-is-free")
def refusal_is_free() -> None:
    """Verify SAFETY_LEDGER ↔ PAYMENT_LEDGER refund-fidelity join."""

    try:
        from orchestrator.billing.ledger import ChainBroken as PaymentChainBroken
        from orchestrator.billing.ledger import iter_rows as iter_payment_rows
        from orchestrator.billing.ledger import verify_chain as verify_payment_chain
        from orchestrator.safety.ledger import ChainBroken as SafetyChainBroken
        from orchestrator.safety.ledger import iter_rows as iter_safety_rows
        from orchestrator.safety.ledger import verify_chain as verify_safety_chain
    except Exception as exc:
        _fail(
            f"cannot import ledger modules: {type(exc).__name__}: {exc}. "
            "The orchestrator.safety or orchestrator.billing library is "
            "not importable."
        )

    try:
        repo_root = find_repo_root(Path.cwd())
    except RepoRootNotFound as exc:
        _fail(f"{exc}")

    safety_path = repo_root / _SAFETY_NAME
    payment_path = repo_root / _PAYMENT_NAME

    safety_present = safety_path.is_file()
    payment_present = payment_path.is_file()

    if not safety_present and not payment_present:
        click.echo(
            "refusal-is-free: OK  no ledgers yet (fresh repo); "
            "Refusal-is-Free is vacuously satisfied."
        )
        raise SystemExit(OK)

    if safety_present != payment_present:
        missing = _SAFETY_NAME if not safety_present else _PAYMENT_NAME
        click.echo(
            f"refusal-is-free: NOT_YET_SEALED — {missing} not present; "
            f"the SAFETY ↔ PAYMENT join cannot be performed. Both "
            f"ledgers must exist for this check."
        )
        raise SystemExit(NOT_YET_SEALED)

    # Property A: per-ledger chain integrity.
    try:
        s_count, _ = verify_safety_chain(safety_path)
    except SafetyChainBroken as exc:
        _fail(
            f"SAFETY_LEDGER chain broken at {exc}. "
            "See docs/04-ARCHITECTURE.md § SAFETY_LEDGER row schema."
        )
    try:
        p_count, _ = verify_payment_chain(payment_path)
    except PaymentChainBroken as exc:
        _fail(
            f"PAYMENT_LEDGER chain broken at {exc}. "
            "See docs/29-BILLING-X402.md § PAYMENT_LEDGER schema."
        )

    # Build join tables.
    safety_by_cid: dict[str, list[dict[str, Any]]] = {}
    for row in iter_safety_rows(safety_path):
        safety_by_cid.setdefault(str(row["correlation_id"]), []).append(row)

    payment_by_cid: dict[str, list[dict[str, Any]]] = {}
    for row in iter_payment_rows(payment_path):
        payment_by_cid.setdefault(str(row["correlation_id"]), []).append(row)

    # Property B + C + D walk. We iterate PAYMENT rows (one per turn,
    # the 5g-iii invariant) and cross-reference the paired SAFETY rows.

    refunded_total = 0
    settled_total = 0
    disabled_total = 0
    refunded_ingress_egress = 0
    refunded_operational = 0
    refunded_by_stage: Counter[str] = Counter()

    for cid, p_rows in payment_by_cid.items():
        # 5g-iii invariant: exactly one PAYMENT row per correlation_id.
        # A second row for the same cid would mean the handler wrote
        # twice for the same turn — a constitutional bug.
        if len(p_rows) > 1:
            _fail(
                f"cid={cid!r}: {len(p_rows)} PAYMENT rows for one "
                f"correlation_id. 5g-iii guarantees exactly one; a "
                f"duplicate means either a retry wrote twice or a "
                f"collision in correlation_id generation."
            )
        p_row = p_rows[0]

        outcome = str(p_row["outcome"])
        posture = str(p_row["posture"])
        refusal_stage = p_row.get("refusal_stage")
        c_xion = int(p_row["committed_XION"])
        s_xion = int(p_row["settled_XION"])
        r_xion = int(p_row["refund_XION"])

        # --- Property B: money-shape (belt-and-suspenders) ---
        # verify_chain already enforces these; re-check here so the
        # Refusal-is-Free verifier has a specific message per property
        # when rows are hand-edited or produced by a future writer
        # that does not route through ``build_payment_row``.
        if c_xion != s_xion + r_xion:
            _fail(
                f"cid={cid!r} seq={p_row['seq']}: money arithmetic "
                f"violation: committed={c_xion} != settled+refund "
                f"({s_xion}+{r_xion}). Property B."
            )
        if outcome == "settled":
            if s_xion != c_xion or r_xion != 0:
                _fail(
                    f"cid={cid!r} seq={p_row['seq']}: outcome=settled "
                    f"requires settled==committed and refund==0; got "
                    f"settled={s_xion}, refund={r_xion}, "
                    f"committed={c_xion}. Property B."
                )
            settled_total += 1
        elif outcome == "refunded":
            if r_xion != c_xion or s_xion != 0:
                _fail(
                    f"cid={cid!r} seq={p_row['seq']}: Refusal-is-Free "
                    f"requires refund==committed and settled==0 for "
                    f"outcome=refunded; got settled={s_xion}, "
                    f"refund={r_xion}, committed={c_xion}. "
                    f"Property B."
                )
            refunded_total += 1
            rs = str(refusal_stage) if refusal_stage is not None else "?"
            refunded_by_stage[rs] += 1
            if rs in _INGRESS_EGRESS:
                refunded_ingress_egress += 1
            else:
                refunded_operational += 1
        else:
            # refunded_partial / stranded are schema-reserved but
            # 5g-iii writer must not emit them. See schema doc.
            _fail(
                f"cid={cid!r} seq={p_row['seq']}: unexpected outcome "
                f"{outcome!r} for 5g-iii writer. See "
                f"docs/schemas/ledger-payment.yaml § outcome."
            )

        if posture == "disabled":
            if c_xion != 0 or s_xion != 0 or r_xion != 0:
                _fail(
                    f"cid={cid!r} seq={p_row['seq']}: posture=disabled "
                    f"requires committed/settled/refund all zero; got "
                    f"{c_xion}/{s_xion}/{r_xion}. Property B."
                )
            disabled_total += 1

        # --- Property C: ingress/egress mirror ---
        paired = safety_by_cid.get(cid, [])

        if outcome == "refunded" and refusal_stage in _INGRESS_EGRESS:
            # There MUST be at least one matching SAFETY verdict=refuse
            # row for this correlation_id (the Arbiter row that drove
            # the refusal). No paired SAFETY row here would mean the
            # Relay refunded a turn the Arbiter never refused — a
            # silent-ingress / silent-egress integrity failure.
            has_refuse = any(
                str(s_row["verdict"]) == "refuse" for s_row in paired
            )
            if not has_refuse:
                seqs = (
                    ",".join(str(s["seq"]) for s in paired)
                    if paired
                    else "<none>"
                )
                _fail(
                    f"cid={cid!r} seq={p_row['seq']}: PAYMENT refused "
                    f"at stage={refusal_stage!r} but NO matching "
                    f"SAFETY verdict=refuse row. paired_safety_seqs="
                    f"{{{seqs}}}. Property C (ingress/egress mirror)."
                )

        # --- Property D: settled implies allowed ---
        if outcome == "settled":
            has_refuse = any(
                str(s_row["verdict"]) == "refuse" for s_row in paired
            )
            if has_refuse:
                seqs = ",".join(
                    str(s["seq"])
                    for s in paired
                    if str(s["verdict"]) == "refuse"
                )
                _fail(
                    f"cid={cid!r} seq={p_row['seq']}: PAYMENT settled "
                    f"but SAFETY carries verdict=refuse row(s) seq="
                    f"{{{seqs}}}. A settled payment for a refused "
                    f"turn is a Covenant-tier integrity break. "
                    f"Property D (settled implies allowed)."
                )

    # Property C (reverse direction): every SAFETY verdict=refuse that
    # has ANY paired PAYMENT row must pair to an outcome=refunded row.
    # The "has any paired PAYMENT row" qualifier skips historic SAFETY
    # rows from before the PAYMENT_LEDGER came live.
    safety_refuse_total = 0
    safety_refuse_unpaired = 0
    for cid, s_rows in safety_by_cid.items():
        refuse_rows = [r for r in s_rows if str(r["verdict"]) == "refuse"]
        if not refuse_rows:
            continue
        safety_refuse_total += len(refuse_rows)
        if cid not in payment_by_cid:
            safety_refuse_unpaired += len(refuse_rows)
            continue
        p_row = payment_by_cid[cid][0]
        if str(p_row["outcome"]) != "refunded":
            s_seqs = ",".join(str(r["seq"]) for r in refuse_rows)
            _fail(
                f"cid={cid!r}: SAFETY verdict=refuse row(s) seq="
                f"{{{s_seqs}}} paired to PAYMENT seq={p_row['seq']} "
                f"outcome={p_row['outcome']!r}, expected 'refunded'. "
                f"Property C (ingress/egress mirror, reverse)."
            )

    # Summary.
    paired_cids = set(safety_by_cid) & set(payment_by_cid)
    click.echo(
        f"refusal-is-free: OK  SAFETY rows={s_count}, PAYMENT rows="
        f"{p_count}; {len(paired_cids)} paired correlation_id(s). "
        f"PAYMENT outcomes: settled={settled_total}, "
        f"refunded={refunded_total} "
        f"(ingress/egress={refunded_ingress_egress}, "
        f"operational={refunded_operational}), "
        f"disabled-posture rows={disabled_total}."
    )
    if refunded_by_stage:
        click.echo("  refund breakdown by refusal_stage:")
        for stage in sorted(refunded_by_stage):
            click.echo(f"    {stage}: {refunded_by_stage[stage]}")
    if safety_refuse_unpaired:
        click.echo(
            f"  note: {safety_refuse_unpaired} SAFETY verdict=refuse "
            f"row(s) have no paired PAYMENT row (pre-PAYMENT_LEDGER "
            f"history); Refusal-is-Free is vacuously satisfied for "
            f"those — no commitment was ever recorded."
        )
    raise SystemExit(OK)


__all__ = ["refusal_is_free"]
