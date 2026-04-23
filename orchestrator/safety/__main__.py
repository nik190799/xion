"""`python -m orchestrator.safety` — Arbiter CLI.

Subcommands:

  gate            Read a candidate from stdin; print the Verdict JSON to
                  stdout. Exit 0 if verdict.egress_allowed else 1.
  serve           Start the loopback TCP server on 127.0.0.1:<port>.
  verify-ledger   Walk SAFETY_LEDGER.jsonl and report chain integrity.
  verify-anchors  Walk SAFETY_LEDGER_ANCHORS.jsonl, verify its hash chain,
                  and cross-check every anchor against the ledger.
  anchor          Run one anchor cycle: evaluate cadence, and if it
                  fires (or --force), publish and append one row.
  principles      Print the principle registry (debug / inspection).

The CLI is a thin wrapper around the library. Every operator-visible
behavior exists as a callable function elsewhere; this file only wires
`argparse` to those functions. A future `xion-cli` can import from here
without re-implementing anything.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from orchestrator.safety import gate
from orchestrator.safety.anchor import (
    AnchorChainBroken,
    AnchorCrossCheckFailed,
    ArweaveSubmitter,
    LocalOnlySubmitter,
    anchor_chain_tip,
    cross_check_anchors_against_ledger,
    run_anchor_once,
    verify_anchor_chain,
)
from orchestrator.safety.ledger import ChainBroken, chain_tip, verify_chain
from orchestrator.safety.principles import principles_summary
from orchestrator.safety.server import DEFAULT_HOST, DEFAULT_PORT, serve_forever
from orchestrator.safety.types import Verdict

_DEFAULT_LEDGER = "SAFETY_LEDGER.jsonl"
_DEFAULT_ANCHORS = "SAFETY_LEDGER_ANCHORS.jsonl"


def _print_verdict_json(v: Verdict) -> None:
    """Serialize a Verdict to the same wire-shape as the TCP server."""
    payload = {
        "decision": v.decision.value,
        "correlation_id": v.correlation_id,
        "candidate_sha256": v.candidate_sha256,
        "timestamp_utc_ns": v.timestamp_utc_ns,
        "summary": v.summary,
        "principle_id": v.principle_id,
        "rule_id": v.rule_id,
        "rule_version": v.rule_version,
        "escalation_reason": v.escalation_reason.value if v.escalation_reason is not None else None,
        "rules_run": list(v.rules_run),
        "egress_allowed": v.egress_allowed,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _cmd_gate(args: argparse.Namespace) -> int:
    candidate = sys.stdin.read()
    ledger_path = Path(args.ledger) if args.ledger else None
    verdict = gate(candidate, correlation_id=args.correlation_id, ledger_path=ledger_path)
    _print_verdict_json(verdict)
    return 0 if verdict.egress_allowed else 1


def _cmd_serve(args: argparse.Namespace) -> int:
    ledger_path = Path(args.ledger) if args.ledger else None
    print(f"Arbiter listening on {args.host}:{args.port} (ledger={ledger_path or 'default'})")
    try:
        serve_forever(host=args.host, port=args.port, ledger_path=ledger_path)
    except KeyboardInterrupt:
        print("\nArbiter: shutdown requested")
        return 0
    return 0


def _cmd_verify_ledger(args: argparse.Namespace) -> int:
    path = Path(args.ledger) if args.ledger else Path("SAFETY_LEDGER.jsonl")
    try:
        count, tip = verify_chain(path)
    except ChainBroken as exc:
        print(f"verify-ledger: FAIL: {exc}", file=sys.stderr)
        return 1
    count_live, tip_live = chain_tip(path)
    # The two methods must agree; if they don't, something very wrong is
    # happening and we fail-closed.
    if count != count_live or tip != tip_live:
        print(
            f"verify-ledger: FAIL: internal inconsistency between "
            f"verify_chain({count}, {tip}) and chain_tip({count_live}, {tip_live})",
            file=sys.stderr,
        )
        return 1
    print(f"verify-ledger: OK  rows={count}  tip={tip}")
    return 0


def _cmd_verify_anchors(args: argparse.Namespace) -> int:
    anchors_path = Path(args.anchors) if args.anchors else Path(_DEFAULT_ANCHORS)
    ledger_path = Path(args.ledger) if args.ledger else Path(_DEFAULT_LEDGER)
    try:
        count, tip = verify_anchor_chain(anchors_path)
    except AnchorChainBroken as exc:
        print(f"verify-anchors: FAIL (chain): {exc}", file=sys.stderr)
        return 1
    # Internal sanity: anchor_chain_tip must agree.
    count_live, tip_live = anchor_chain_tip(anchors_path)
    if count != count_live or tip != tip_live:
        print(
            f"verify-anchors: FAIL: internal inconsistency between "
            f"verify_anchor_chain({count}, {tip}) and anchor_chain_tip({count_live}, {tip_live})",
            file=sys.stderr,
        )
        return 1
    # Structural chain is OK. Now cross-check against the ledger.
    try:
        a_count, rows_covered = cross_check_anchors_against_ledger(anchors_path, ledger_path)
    except AnchorCrossCheckFailed as exc:
        print(f"verify-anchors: FAIL (cross-check): {exc}", file=sys.stderr)
        return 1
    ledger_count, _ = chain_tip(ledger_path)
    truncation_window = max(0, ledger_count - rows_covered)
    print(
        f"verify-anchors: OK  anchors={count}  tip={tip}  "
        f"rows_covered={rows_covered}/{ledger_count}  truncation_window={truncation_window}"
    )
    if a_count != count:
        # Should be impossible but name it if it happens.
        print(
            f"verify-anchors: WARN: verify_anchor_chain count={count} != "
            f"cross_check count={a_count}",
            file=sys.stderr,
        )
    return 0


def _cmd_anchor(args: argparse.Namespace) -> int:
    anchors_path = Path(args.anchors) if args.anchors else Path(_DEFAULT_ANCHORS)
    ledger_path = Path(args.ledger) if args.ledger else Path(_DEFAULT_LEDGER)
    submitter = _build_submitter_from_args(args)
    try:
        result = run_anchor_once(
            anchors_path=anchors_path,
            ledger_path=ledger_path,
            submitter=submitter,
            force=args.force,
        )
    except Exception as exc:
        # Any submitter exception surfaces as nonzero exit. The anchors
        # file is not touched (no partial writes), preserving the
        # "honest record; no false claims of having anchored" property.
        print(f"anchor: FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    if result.anchored:
        assert result.row is not None
        print(
            f"anchor: OK  trigger={result.trigger}  "
            f"seq={result.row['seq']}  "
            f"submitted_to={result.row['submitted_to']}  "
            f"ar_tx_id={result.row.get('ar_tx_id') or '-'}"
        )
    else:
        print(f"anchor: SKIP  reason={result.reason}")
    return 0


def _build_submitter_from_args(args: argparse.Namespace):
    """Select submitter: local-only by default; arweave if --arweave.

    Honest about what each choice means: passing --arweave without a
    configured wallet will fail at submit time and exit nonzero, not
    silently downgrade to local. The operator is the one making that
    choice.
    """
    if args.arweave:
        return ArweaveSubmitter(
            jwk_path=args.wallet_jwk,
            gateway=args.arweave_gateway,
        )
    return LocalOnlySubmitter()


def _cmd_principles(args: argparse.Namespace) -> int:
    print(principles_summary())
    return 0


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m orchestrator.safety",
        description="The Arbiter — Covenant enforcement pipeline (Phase 4a).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("gate", help="Gate one candidate from stdin.")
    g.add_argument("--correlation-id", required=True,
                   help="Caller-provided opaque id; pairs with refund flow.")
    g.add_argument("--ledger", default=None,
                   help="Override SAFETY_LEDGER.jsonl path.")
    g.set_defaults(func=_cmd_gate)

    s = sub.add_parser("serve", help="Run the loopback TCP server.")
    s.add_argument("--host", default=DEFAULT_HOST,
                   help=f"Loopback host to bind (default {DEFAULT_HOST}). Non-loopback rejected.")
    s.add_argument("--port", type=int, default=DEFAULT_PORT,
                   help=f"TCP port (default {DEFAULT_PORT}).")
    s.add_argument("--ledger", default=None,
                   help="Override SAFETY_LEDGER.jsonl path.")
    s.set_defaults(func=_cmd_serve)

    v = sub.add_parser("verify-ledger", help="Walk the ledger and verify the hash chain.")
    v.add_argument("--ledger", default=None,
                   help="Ledger path (default ./SAFETY_LEDGER.jsonl).")
    v.set_defaults(func=_cmd_verify_ledger)

    va = sub.add_parser(
        "verify-anchors",
        help="Verify SAFETY_LEDGER_ANCHORS and cross-check against the ledger.",
    )
    va.add_argument("--anchors", default=None,
                    help="Anchors path (default ./SAFETY_LEDGER_ANCHORS.jsonl).")
    va.add_argument("--ledger", default=None,
                    help="Ledger path (default ./SAFETY_LEDGER.jsonl).")
    va.set_defaults(func=_cmd_verify_anchors)

    an = sub.add_parser(
        "anchor",
        help="Evaluate cadence and, if fired (or --force), publish one anchor row.",
    )
    an.add_argument("--anchors", default=None,
                    help="Anchors path (default ./SAFETY_LEDGER_ANCHORS.jsonl).")
    an.add_argument("--ledger", default=None,
                    help="Ledger path (default ./SAFETY_LEDGER.jsonl).")
    an.add_argument("--force", action="store_true",
                    help="Bypass cadence; anchor immediately (labels trigger=startup).")
    an.add_argument("--arweave", action="store_true",
                    help="Use ArweaveSubmitter instead of the LocalOnlySubmitter default.")
    an.add_argument("--wallet-jwk", default=None,
                    help="Override $XION_ANCHOR_WALLET_JWK_PATH for --arweave.")
    an.add_argument("--arweave-gateway", default=None,
                    help="Override $XION_ANCHOR_ARWEAVE_GATEWAY (default https://arweave.net).")
    an.set_defaults(func=_cmd_anchor)

    pr = sub.add_parser("principles", help="Print the principle registry.")
    pr.set_defaults(func=_cmd_principles)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
