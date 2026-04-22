"""`xion-verify refusal-rate` — verdict-counts on SAFETY_LEDGER (Phase 5a live).

Reads SAFETY_LEDGER.jsonl, walks the chain (delegating to the Arbiter's
own `verify_chain`), and tallies:

  - total verdicts by Decision (ok / refuse / escalate),
  - escalate breakdown by `escalation_reason`,
  - REFUSE breakdown by source: v1 rule (rule_id non-null) vs v2 (v2-
    produced; identifiable as REFUSE rows with rule_id null and a
    non-null llm_verdict.decision == 'refuse').

Operators and auditors use this to see degraded-mode events (rates of
`arbiter_timeout` / `arbiter_unreachable` / `ruleset_uncaught_exception`)
as first-class telemetry rather than buried in log lines.

What this verifier does NOT do (intentionally, with an honest pointer):

  * Without `--corpus`, it does not compare the operator ledger against
    the `xion-audit/baseline_corpus/` labels. With `--corpus`, it
    re-runs v1 `apply_rules` against the baseline and FAILs on the first
    item whose outcome disagrees with the recorded expectation (the
    same check as `xion-audit measure` for v1).
  * It does not compute a time-series. A rolling-30-day window is
    deferred until the ledger is large enough that flat tallies stop
    being legible.

Exit codes:

  0 OK              SAFETY_LEDGER read successfully (or absent — fresh
                    repo). Tallies printed.
  1 FAIL            SAFETY_LEDGER chain broken (delegated to
                    `orchestrator.safety.ledger.verify_chain`).
  2 NOT_YET_SEALED  never returned (the verifier is unconditionally
                    runnable; absence of the ledger is reported as
                    OK with zero verdicts).
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import click

from xion_verify.exit_codes import FAIL, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root

_SAFETY_NAME = "SAFETY_LEDGER.jsonl"

_DEGRADED_REASONS: frozenset[str] = frozenset({
    "arbiter_timeout",
    "arbiter_unreachable",
    "ruleset_uncaught_exception",
    "llm_arbiter_uncaught_exception",
    "llm_arbiter_provider_unavailable",
})
"""Escalation reasons that signal an integration / pipeline failure
rather than a Covenant judgement. Operators page on these."""


def _fail(message: str) -> None:
    click.echo(f"refusal-rate: FAIL: {message}", err=True)
    raise SystemExit(FAIL)


def _refusal_rate_corpus() -> None:
    from orchestrator.audit_corpus import load_repo_corpus
    from orchestrator.safety.rules import apply_rules
    from orchestrator.safety.types import Decision

    try:
        root = find_repo_root(Path.cwd())
    except RepoRootNotFound as exc:
        _fail(f"{exc}")
    try:
        items = load_repo_corpus(root)
    except Exception as exc:
        _fail(
            f"cannot load baseline corpus: {type(exc).__name__}: {exc} "
            f"(is xion-audit/baseline_corpus/ present?)"
        )
    n = 0
    for it in items:
        rr, _ = apply_rules(it.candidate)
        if it.expected_decision == "ok":
            if rr.decision is not Decision.OK:
                _fail(f"{it.item_id}: expected ok got {rr.decision}")
        elif it.expected_decision == "refuse":
            if rr.decision is not Decision.REFUSE or rr.principle_id != it.expected_principle_id:
                _fail(
                    f"{it.item_id}: expected refuse/{it.expected_principle_id!r} "
                    f"got {rr.decision} {getattr(rr, 'principle_id', None)}"
                )
        else:
            if rr.decision is not Decision.ESCALATE or rr.principle_id != it.expected_principle_id:
                _fail(
                    f"{it.item_id}: expected escalate/{it.expected_principle_id!r} "
                    f"got {rr.decision} {getattr(rr, 'principle_id', None)}"
                )
        n += 1
    click.echo(
        f"refusal-rate: OK  corpus mode — {n} v1 item(s) match expected labels in "
        f"xion-audit/baseline_corpus/ (see `xion-audit measure` for the same check)."
    )
    raise SystemExit(OK)


@click.command(name="refusal-rate")
@click.option(
    "--corpus",
    is_flag=True,
    help="Verify the Phase 4e baseline corpus: v1 `apply_rules` vs expected labels (no ledger read).",
)
def refusal_rate(corpus: bool) -> None:
    """Tally SAFETY_LEDGER verdicts and degraded-mode rates."""

    if corpus:
        _refusal_rate_corpus()
        return

    try:
        from orchestrator.safety.ledger import ChainBroken, iter_rows, verify_chain
    except Exception as exc:
        _fail(
            f"cannot import orchestrator.safety.ledger: {type(exc).__name__}: {exc}"
        )

    try:
        repo_root = find_repo_root(Path.cwd())
    except RepoRootNotFound as exc:
        _fail(f"{exc}")

    safety_path = repo_root / _SAFETY_NAME
    if not safety_path.is_file():
        click.echo(
            "refusal-rate: OK  no SAFETY_LEDGER yet (no verdicts rendered); "
            "totals=0 / 0 / 0 (ok / refuse / escalate)."
        )
        raise SystemExit(OK)

    try:
        verify_chain(safety_path)
    except ChainBroken as exc:
        _fail(
            f"SAFETY_LEDGER chain broken at {exc}. "
            "Tallies cannot be trusted on a tampered ledger."
        )

    decision_counts: Counter[str] = Counter()
    refuse_v1 = 0
    refuse_v2 = 0
    escalate_reasons: Counter[str] = Counter()

    for row in iter_rows(safety_path):
        verdict = str(row["verdict"])
        decision_counts[verdict] += 1
        if verdict == "refuse":
            if row.get("rule_id"):
                refuse_v1 += 1
            else:
                refuse_v2 += 1
        elif verdict == "escalate":
            reason = row.get("escalation_reason")
            escalate_reasons[str(reason) if reason else "<unspecified>"] += 1

    total = sum(decision_counts.values())
    degraded = sum(escalate_reasons[r] for r in _DEGRADED_REASONS)

    click.echo(
        f"refusal-rate: OK  {total} verdict(s); "
        f"ok={decision_counts.get('ok', 0)}, "
        f"refuse={decision_counts.get('refuse', 0)} (v1={refuse_v1}, v2={refuse_v2}), "
        f"escalate={decision_counts.get('escalate', 0)}; "
        f"degraded-mode signals={degraded}"
    )
    if escalate_reasons:
        # One line per reason, sorted so the output is stable across runs.
        click.echo("  escalation_reason breakdown:")
        for reason in sorted(escalate_reasons):
            click.echo(f"    {reason}: {escalate_reasons[reason]}")
    raise SystemExit(OK)
