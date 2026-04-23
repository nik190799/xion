"""``xion-verify chat-streaming-fidelity`` — stream-level invariants (Phase 5g-ii Commit 5).

Walks ``PAYMENT_LEDGER.jsonl`` and ``SAFETY_LEDGER.jsonl`` and asserts
the stream-level invariants pinned in ``docs/04-ARCHITECTURE.md``
§ "Streaming the Chat Surface (Phase 5g-ii)",
``docs/32-CHAT-STREAMING.md``, and the PAYMENT_LEDGER schema in
``docs/schemas/ledger-payment.yaml``.

Properties promised (every streaming turn that has executed since
``POST /chat/stream`` came live):

  A. Per-ledger chain integrity — both ledgers' ``verify_chain``
     disciplines pass. A tampered ledger invalidates every claim below.
     (The ``refusal-is-free`` verifier also asserts this; we re-assert
     here so this command is self-contained and can be invoked alone.)

  B. Stream identification —
     * every PAYMENT row with ``stream_id`` present has ``stream_id``
       in the 32-hex form (byte-exact match against the schema);
     * every PAYMENT row with ``outcome=cancelled`` has ``stream_id``
       present (cancel is stream-only; a cancel row without a
       ``stream_id`` is a constitutional bug);
     * every PAYMENT row without ``stream_id`` has
       ``outcome != cancelled`` (the non-streaming ``POST /chat``
       handler never emits ``cancelled``).

  C. One PAYMENT row per stream — for every observed ``stream_id``,
     exactly one PAYMENT row carries it. A ``stream_id`` on two rows
     would mean two payment writes for one stream, breaking the
     single-row-per-turn contract specifically for streams.

  D. Money-shape (re-asserted from ``refusal-is-free`` for the
     streaming subset so operators see a specific, stream-scoped
     message on failure):
       * ``outcome=settled``   → settled==committed, refund=0.
       * ``outcome=refunded``  → refund==committed,  settled=0,
         refusal_stage IS NOT NULL.
       * ``outcome=cancelled`` → refund==committed,  settled=0,
         refusal_stage IS NULL.

  E. Cancel-without-paired-refuse — for every stream with
     ``outcome=cancelled``, there is NO paired SAFETY row with
     ``verdict=refuse`` at the stream's ``correlation_id``. The
     ingress Arbiter call completed (cancel only fires after the
     stream opened, which requires ingress approval); egress
     moderation never ran (the client gave up before generation
     completed). No SAFETY refuse row can legitimately exist for
     a cancelled stream's ``correlation_id``.

  F. Egress-refuse-with-paired-refuse — for every stream with
     ``outcome=refunded`` AND ``refusal_stage=egress``, there IS at
     least one paired SAFETY row with ``verdict=refuse`` at the
     stream's ``correlation_id``. The retroactive-refusal path
     structurally requires the paired row (egress moderation on the
     buffered complete candidate returned refuse; SAFETY must have
     recorded it). Ingress for an egress-refused turn was
     approved, so the only refuse row is the egress one.

Exit codes:

  0 OK              every required property holds for every streaming
                    row, OR no streaming rows yet (NOT_YET_SEALED
                    fall-through to OK is NOT taken — see below).
  1 FAIL            structural mismatch, broken chain, money-shape
                    violation, duplicate ``stream_id``, or missing /
                    extra paired SAFETY row. Message names the
                    offending ``stream_id`` and the specific property.
  2 NOT_YET_SEALED  (a) no PAYMENT_LEDGER on disk yet, OR
                    (b) PAYMENT_LEDGER present but no row carries a
                        ``stream_id`` (no streaming turn executed yet).

  Returning OK in state (b) would silently claim a property we never
  exercised. The NOT_YET_SEALED posture is the honest signal: "the
  verifier is wired and the ledgers are sound, but no streaming turn
  has yet been billed so the stream-level properties are not yet
  sealed by any on-disk evidence." The first billed streaming turn
  promotes the command to OK automatically.

What this verifier does NOT do (with honest pointers):

  * It does not cross-walk the REQUEST_LEDGER. REQUEST ↔ SAFETY is
    ``xion-verify refund-fidelity`` territory; at Phase 5g-ii the
    join would be a property-check copy, not a new check.
  * It does not assert that chunks were actually streamed. That is a
    client-visible property (the client's Fetch body iterated more
    than once); the server does not log per-chunk bytes. The
    ``chat_stream.py`` handler's single-``done``-per-stream shape is
    enforced by type (one call to ``_finalize_stream_ledger`` per
    generator run), not by ledger walk.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import click

from xion_verify.exit_codes import FAIL, NOT_YET_SEALED, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root

_SAFETY_NAME = "SAFETY_LEDGER.jsonl"
_PAYMENT_NAME = "PAYMENT_LEDGER.jsonl"


def _fail(message: str) -> None:
    click.echo(f"chat-streaming-fidelity: FAIL: {message}", err=True)
    raise SystemExit(FAIL)


def _is_valid_stream_id(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 32
        and all(c in "0123456789abcdef" for c in value)
    )


@click.command(name="chat-streaming-fidelity")
def chat_streaming_fidelity() -> None:
    """Verify PAYMENT_LEDGER ↔ SAFETY_LEDGER stream-level invariants."""

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

    if not payment_path.is_file():
        click.echo(
            "chat-streaming-fidelity: NOT_YET_SEALED  no PAYMENT_LEDGER "
            "on disk yet; no streaming turn has been billed. The "
            "stream-level invariants are not yet sealed by on-disk "
            "evidence; the first billed streaming turn promotes this "
            "command to OK automatically."
        )
        raise SystemExit(NOT_YET_SEALED)

    # Property A: per-ledger chain integrity.
    try:
        p_count, _ = verify_payment_chain(payment_path)
    except PaymentChainBroken as exc:
        _fail(
            f"PAYMENT_LEDGER chain broken at {exc}. "
            "See docs/29-BILLING-X402.md § PAYMENT_LEDGER schema."
        )

    safety_by_cid: dict[str, list[dict[str, Any]]] = {}
    if safety_path.is_file():
        try:
            verify_safety_chain(safety_path)
        except SafetyChainBroken as exc:
            _fail(
                f"SAFETY_LEDGER chain broken at {exc}. "
                "See docs/04-ARCHITECTURE.md § SAFETY_LEDGER row schema."
            )
        for row in iter_safety_rows(safety_path):
            safety_by_cid.setdefault(str(row["correlation_id"]), []).append(row)
    # SAFETY may be absent on a brand-new repo that has only emitted
    # ``outcome=cancelled`` streams (no Arbiter rows would be written
    # if the Relay was disabled — but the Arbiter runs on ingress
    # before any stream opens, so in practice SAFETY is present
    # whenever PAYMENT is). We treat SAFETY-absent as OK for the
    # stream-level walk but skip properties E and F.

    # Build the stream index.
    rows_by_stream: dict[str, list[dict[str, Any]]] = defaultdict(list)
    stream_rows_total = 0
    cancelled_without_stream_id: list[dict[str, Any]] = []
    non_stream_cancelled: list[dict[str, Any]] = []

    for row in iter_payment_rows(payment_path):
        outcome = str(row["outcome"])
        stream_id = row.get("stream_id")

        if stream_id is None:
            if outcome == "cancelled":
                cancelled_without_stream_id.append(row)
            continue

        if not _is_valid_stream_id(stream_id):
            _fail(
                f"seq={row['seq']}: stream_id={stream_id!r} is not 32 "
                f"lowercase hex chars. Property B (stream identification)."
            )
        rows_by_stream[stream_id].append(row)
        stream_rows_total += 1

    if cancelled_without_stream_id:
        seqs = ",".join(str(r["seq"]) for r in cancelled_without_stream_id)
        _fail(
            f"seq={{{seqs}}}: outcome=cancelled rows without stream_id. "
            "Cancellation is stream-only; a cancel row without a "
            "stream_id is a constitutional bug. "
            "Property B (stream identification)."
        )

    if stream_rows_total == 0:
        click.echo(
            f"chat-streaming-fidelity: NOT_YET_SEALED  PAYMENT_LEDGER "
            f"has {p_count} row(s) but none carry stream_id; no "
            "streaming turn has been billed. The stream-level "
            "invariants are not yet sealed by on-disk evidence; the "
            "first billed streaming turn promotes this command to OK "
            "automatically."
        )
        raise SystemExit(NOT_YET_SEALED)

    settled = refunded = cancelled = 0
    refused_by_stage: Counter[str] = Counter()

    for stream_id, p_rows in rows_by_stream.items():
        # Property C: one row per stream_id.
        if len(p_rows) > 1:
            seqs = ",".join(str(r["seq"]) for r in p_rows)
            _fail(
                f"stream_id={stream_id!r}: {len(p_rows)} PAYMENT rows "
                f"for one stream_id (seq={{{seqs}}}). "
                "Property C (one-row-per-stream)."
            )
        p_row = p_rows[0]
        outcome = str(p_row["outcome"])
        refusal_stage = p_row.get("refusal_stage")
        cid = str(p_row["correlation_id"])
        c_xion = int(p_row["committed_XION"])
        s_xion = int(p_row["settled_XION"])
        r_xion = int(p_row["refund_XION"])

        # Property D: money-shape (stream subset).
        if c_xion != s_xion + r_xion:
            _fail(
                f"stream_id={stream_id!r} seq={p_row['seq']}: money "
                f"arithmetic violation: committed={c_xion} != "
                f"settled+refund ({s_xion}+{r_xion}). Property D."
            )
        if outcome == "settled":
            if s_xion != c_xion or r_xion != 0 or refusal_stage is not None:
                _fail(
                    f"stream_id={stream_id!r} seq={p_row['seq']}: "
                    f"outcome=settled requires settled==committed, "
                    f"refund=0, refusal_stage=null; got settled={s_xion}, "
                    f"refund={r_xion}, refusal_stage={refusal_stage!r}. "
                    "Property D."
                )
            settled += 1
        elif outcome == "refunded":
            if r_xion != c_xion or s_xion != 0 or refusal_stage is None:
                _fail(
                    f"stream_id={stream_id!r} seq={p_row['seq']}: "
                    f"outcome=refunded requires refund==committed, "
                    f"settled=0, refusal_stage non-null; got "
                    f"settled={s_xion}, refund={r_xion}, "
                    f"refusal_stage={refusal_stage!r}. Property D."
                )
            refunded += 1
            refused_by_stage[str(refusal_stage)] += 1
        elif outcome == "cancelled":
            if r_xion != c_xion or s_xion != 0 or refusal_stage is not None:
                _fail(
                    f"stream_id={stream_id!r} seq={p_row['seq']}: "
                    f"outcome=cancelled requires refund==committed, "
                    f"settled=0, refusal_stage=null; got "
                    f"settled={s_xion}, refund={r_xion}, "
                    f"refusal_stage={refusal_stage!r}. Property D."
                )
            cancelled += 1
        else:
            _fail(
                f"stream_id={stream_id!r} seq={p_row['seq']}: "
                f"unexpected outcome {outcome!r} for a streaming row. "
                "5g-ii writers emit settled/refunded/cancelled only."
            )

        paired = safety_by_cid.get(cid, [])
        paired_refuse = [
            s_row for s_row in paired if str(s_row.get("verdict")) == "refuse"
        ]

        # Property E: cancel-without-paired-refuse.
        if outcome == "cancelled" and paired_refuse:
            seqs = ",".join(str(s["seq"]) for s in paired_refuse)
            _fail(
                f"stream_id={stream_id!r} cid={cid!r}: "
                f"outcome=cancelled but SAFETY carries "
                f"verdict=refuse row(s) seq={{{seqs}}}. Cancel fires "
                f"after the stream opened (so ingress was approved) "
                f"and before egress (so egress never ran); no "
                f"refuse row can legitimately pair to this cid. "
                "Property E (cancel-without-paired-refuse)."
            )

        # Property F: egress-refuse-with-paired-refuse.
        if outcome == "refunded" and str(refusal_stage) == "egress":
            if not paired_refuse:
                s_seqs = (
                    ",".join(str(s["seq"]) for s in paired)
                    if paired
                    else "<none>"
                )
                _fail(
                    f"stream_id={stream_id!r} cid={cid!r}: PAYMENT "
                    f"refused at stage=egress but NO matching SAFETY "
                    f"verdict=refuse row. paired_safety_seqs="
                    f"{{{s_seqs}}}. Property F "
                    "(egress-refuse-with-paired-refuse)."
                )

    click.echo(
        f"chat-streaming-fidelity: OK  {stream_rows_total} streaming "
        f"PAYMENT row(s) across {len(rows_by_stream)} stream_id(s). "
        f"outcomes: settled={settled}, refunded={refunded}, "
        f"cancelled={cancelled}."
    )
    if refused_by_stage:
        click.echo("  refused breakdown by refusal_stage:")
        for stage in sorted(refused_by_stage):
            click.echo(f"    {stage}: {refused_by_stage[stage]}")
    raise SystemExit(OK)


__all__ = ["chat_streaming_fidelity"]
