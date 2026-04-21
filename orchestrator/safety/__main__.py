"""`python -m orchestrator.safety` — Arbiter CLI.

Subcommands:

  gate            Read a candidate from stdin; print the Verdict JSON to
                  stdout. Exit 0 if verdict.egress_allowed else 1.
  serve           Start the loopback TCP server on 127.0.0.1:<port>.
  verify-ledger   Walk SAFETY_LEDGER.jsonl and report chain integrity.
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
from orchestrator.safety.ledger import ChainBroken, chain_tip, verify_chain
from orchestrator.safety.principles import principles_summary
from orchestrator.safety.server import DEFAULT_HOST, DEFAULT_PORT, serve_forever
from orchestrator.safety.types import Verdict


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

    pr = sub.add_parser("principles", help="Print the principle registry.")
    pr.set_defaults(func=_cmd_principles)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
