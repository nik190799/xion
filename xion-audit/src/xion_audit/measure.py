"""`xion-audit measure` — v1 (and optional v2) against `baseline_corpus/`.

Two distinct operating modes:

* **Gate mode** (default). Walks every baseline item, runs v1
  `apply_rules`, and FAILs on the first `(decision, principle_id)` that
  disagrees with the item's pinned expectation. This is the same
  invariant `xion-verify refusal-rate --corpus` enforces; `xion-audit
  measure` is the auditor-facing copy (operator vs. auditor split —
  both see the same truth).
* **Confusion-matrix mode** (`--confusion`). Surfaces per-principle
  precision / recall / confusion counts without short-circuiting on the
  first disagreement. This is the numeric claim the Arbiter is
  *allowed to make about itself* once the corpus is large enough to
  justify it; at 78 items the numbers are suggestive, not authoritative
  (see `KW-ARBITER-005` for the ≥ 200-item bar). Emitted in both
  human-readable and `--json` shapes so a CI job can regress on the
  counts.

Neither mode calls the network unless `--v2=chutes-llm-judge` is
passed AND `XION_CHUTES_API_KEY` is set; in confusion-matrix mode with v2,
per-principle counts for v2's decisions on v1-OK items are added as a
separate section (v2 is a second-pass classifier, not a replacement).
"""

from __future__ import annotations

import json
import os
from typing import Any

import click

from xion_audit.repo import find_repo_root_or_cwd


@click.command("measure")
@click.option(
    "--v2",
    "v2_provider",
    type=str,
    default="",
    help="If set to 'chutes-llm-judge', run v2 on v1-OK items (requires XION_CHUTES_API_KEY for live calls).",
)
@click.option(
    "--confusion",
    is_flag=True,
    help="Emit per-principle confusion matrix (non-failing) instead of first-disagreement gate.",
)
@click.option(
    "--json",
    "json_out",
    is_flag=True,
    help="With --confusion, emit a single JSON object on stdout instead of a human-readable report.",
)
def measure(v2_provider: str, confusion: bool, json_out: bool) -> None:
    from orchestrator.audit_corpus import load_repo_corpus
    from orchestrator.safety.rules import apply_rules
    from orchestrator.safety.types import Decision

    try:
        repo = find_repo_root_or_cwd()
    except FileNotFoundError as e:
        click.echo(f"measure: FAIL: {e}", err=True)
        raise SystemExit(1) from e

    items = load_repo_corpus(repo)

    if confusion:
        _measure_confusion(items, v2_provider, json_out)
        return

    ok_n = 0
    for it in items:
        rr, _ = apply_rules(it.candidate)
        if it.expected_decision == "ok":
            if rr.decision is not Decision.OK:
                click.echo(
                    f"measure: FAIL: {it.item_id} expected ok got {rr.decision}",
                    err=True,
                )
                raise SystemExit(1)
        elif it.expected_decision == "refuse":
            if rr.decision is not Decision.REFUSE or rr.principle_id != it.expected_principle_id:
                click.echo(
                    f"measure: FAIL: {it.item_id} expected refuse/{it.expected_principle_id!r} "
                    f"got {rr.decision} {getattr(rr, 'principle_id', None)}",
                    err=True,
                )
                raise SystemExit(1)
        else:
            if rr.decision is not Decision.ESCALATE or rr.principle_id != it.expected_principle_id:
                click.echo(
                    f"measure: FAIL: {it.item_id} expected escalate/{it.expected_principle_id!r} "
                    f"got {rr.decision} {getattr(rr, 'principle_id', None)}",
                    err=True,
                )
                raise SystemExit(1)
        ok_n += 1

    v2_line = ""
    v2_measured = 0
    if v2_provider.strip() == "chutes-llm-judge":
        if not os.environ.get("XION_CHUTES_API_KEY", "").strip():
            v2_line = " v2_chutes: NOT_MEASURED (XION_CHUTES_API_KEY not set; export it to run v2 on v1-OK items)."
        else:
            from orchestrator.safety.providers.chutes_llm_judge import ChutesLlmJudgeProvider

            p = ChutesLlmJudgeProvider()
            for it in items:
                rr, _ = apply_rules(it.candidate)
                if rr.decision is not Decision.OK:
                    continue
                v2_measured += 1
                p.judge(it.candidate)
            v2_line = f" v2_chutes: measured={v2_measured} (spot-check: provider {p.provider_id} v{p.provider_version})"

    click.echo(
        f"measure: OK  v1 exact-match on {ok_n} baseline item(s) against `apply_rules`."
        f"{v2_line}"
    )
    raise SystemExit(0)


# --------------------------------------------------------------------------
# Confusion-matrix mode.
# --------------------------------------------------------------------------

# Decisions recorded on every (predicted, expected) pair, per principle.
# We record counts by *principle*: for a ground-truth principle `p`, a
# prediction is a "hit" iff the predicted decision AND principle match
# the expected decision AND principle. This is the only honest shape
# for the Arbiter, because a "refuse but wrong principle" is *not*
# equivalent to a correct refusal — the row that lands in the ledger
# carries the wrong principle id and a downstream auditor would misread
# which Covenant clause was invoked.


def _stat_block() -> dict[str, int]:
    return {"tp": 0, "fp": 0, "fn": 0, "wrong_principle": 0}


def _measure_confusion(items: list, v2_provider: str, json_out: bool) -> None:
    from orchestrator.safety.rules import apply_rules
    from orchestrator.safety.types import Decision

    v1_stats: dict[str, dict[str, int]] = {}
    v1_support: dict[str, int] = {}
    benign_total = 0
    benign_false_positives = 0

    for it in items:
        rr, _ = apply_rules(it.candidate)
        got_decision = rr.decision
        got_principle = getattr(rr, "principle_id", None)

        if it.expected_decision == "ok":
            benign_total += 1
            if got_decision is not Decision.OK:
                benign_false_positives += 1
                pid = got_principle or "<unknown>"
                s = v1_stats.setdefault(pid, _stat_block())
                s["fp"] += 1
            continue

        pid_expected = it.expected_principle_id or "<unknown>"
        v1_support[pid_expected] = v1_support.get(pid_expected, 0) + 1
        s = v1_stats.setdefault(pid_expected, _stat_block())

        want_dec = Decision.REFUSE if it.expected_decision == "refuse" else Decision.ESCALATE
        if got_decision is want_dec and got_principle == pid_expected:
            s["tp"] += 1
        elif got_decision is Decision.OK:
            s["fn"] += 1
        else:
            # Fired, but on the wrong principle OR wrong decision class.
            s["wrong_principle"] += 1
            if got_principle and got_principle != pid_expected:
                other = v1_stats.setdefault(got_principle, _stat_block())
                other["fp"] += 1

    report: dict[str, Any] = {
        "version": 1,
        "corpus_size": len(items),
        "benign_total": benign_total,
        "benign_false_positives": benign_false_positives,
        "v1": _format_per_principle(v1_stats, v1_support),
    }

    v2_block = _maybe_run_v2(items, v2_provider)
    if v2_block is not None:
        report["v2"] = v2_block

    if json_out:
        click.echo(json.dumps(report, sort_keys=True, indent=2))
        raise SystemExit(0)

    _print_human(report)
    raise SystemExit(0)


def _format_per_principle(
    stats: dict[str, dict[str, int]], support: dict[str, int]
) -> dict[str, Any]:
    out: dict[str, Any] = {"per_principle": {}, "summary": {}}
    total_tp = total_fp = total_fn = total_wp = 0
    for pid in sorted(stats.keys()):
        s = stats[pid]
        tp = s["tp"]
        fp = s["fp"]
        fn = s["fn"]
        wp = s["wrong_principle"]
        precision = _safe_div(tp, tp + fp)
        recall = _safe_div(tp, tp + fn + wp)
        out["per_principle"][pid] = {
            "support": support.get(pid, 0),
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "wrong_principle": wp,
            "precision": precision,
            "recall": recall,
        }
        total_tp += tp
        total_fp += fp
        total_fn += fn
        total_wp += wp
    out["summary"] = {
        "tp_total": total_tp,
        "fp_total": total_fp,
        "fn_total": total_fn,
        "wrong_principle_total": total_wp,
        "micro_precision": _safe_div(total_tp, total_tp + total_fp),
        "micro_recall": _safe_div(total_tp, total_tp + total_fn + total_wp),
    }
    return out


def _safe_div(n: int, d: int) -> float | None:
    if d <= 0:
        return None
    return round(n / d, 4)


def _maybe_run_v2(items: list, v2_provider: str) -> dict[str, Any] | None:
    if v2_provider.strip().lower() != "chutes-llm-judge":
        return None
    if not os.environ.get("XION_CHUTES_API_KEY", "").strip():
        return {
            "status": "NOT_MEASURED",
            "reason": "XION_CHUTES_API_KEY not set; export it to run v2 on v1-OK items.",
        }

    from orchestrator.safety.providers.chutes_llm_judge import ChutesLlmJudgeProvider
    from orchestrator.safety.rules import apply_rules
    from orchestrator.safety.types import Decision

    p = ChutesLlmJudgeProvider()
    v2_support: dict[str, int] = {}
    v2_stats: dict[str, dict[str, int]] = {}
    v2_benign_total = 0
    v2_benign_false_positives = 0
    measured = 0
    errors = 0

    for it in items:
        # v2 runs on the same v1-OK surface the pipeline actually hits.
        rr, _ = apply_rules(it.candidate)
        if rr.decision is not Decision.OK:
            continue
        try:
            j = p.judge(it.candidate)
        except Exception:
            errors += 1
            continue
        measured += 1

        if it.expected_decision == "ok":
            v2_benign_total += 1
            if j.decision is not Decision.OK:
                v2_benign_false_positives += 1
                pid = j.principle_id or "<unknown>"
                v2_stats.setdefault(pid, _stat_block())["fp"] += 1
            continue

        pid_expected = it.expected_principle_id or "<unknown>"
        v2_support[pid_expected] = v2_support.get(pid_expected, 0) + 1
        s = v2_stats.setdefault(pid_expected, _stat_block())
        want_dec = Decision.REFUSE if it.expected_decision == "refuse" else Decision.ESCALATE
        if j.decision is want_dec and j.principle_id == pid_expected:
            s["tp"] += 1
        elif j.decision is Decision.OK:
            s["fn"] += 1
        else:
            s["wrong_principle"] += 1
            if j.principle_id and j.principle_id != pid_expected:
                v2_stats.setdefault(j.principle_id, _stat_block())["fp"] += 1

    out = _format_per_principle(v2_stats, v2_support)
    out["status"] = "MEASURED"
    out["provider_id"] = p.provider_id
    out["provider_version"] = p.provider_version
    out["measured"] = measured
    out["errors"] = errors
    out["benign_total"] = v2_benign_total
    out["benign_false_positives"] = v2_benign_false_positives
    return out


def _print_human(report: dict[str, Any]) -> None:
    click.echo(
        f"measure (confusion): corpus_size={report['corpus_size']} "
        f"benign_total={report['benign_total']} "
        f"benign_false_positives={report['benign_false_positives']}"
    )
    _print_section("v1 (apply_rules)", report["v1"])
    if "v2" in report:
        v2 = report["v2"]
        if v2.get("status") == "NOT_MEASURED":
            click.echo(f"v2: NOT_MEASURED — {v2.get('reason', '')}")
        else:
            click.echo(
                f"v2 ({v2.get('provider_id')} v{v2.get('provider_version')}): "
                f"measured={v2.get('measured', 0)} errors={v2.get('errors', 0)} "
                f"benign_total={v2.get('benign_total', 0)} "
                f"benign_false_positives={v2.get('benign_false_positives', 0)}"
            )
            _print_section("v2", v2)
    click.echo(
        "note: with a corpus of <200 items these numbers are suggestive, "
        "not authoritative. See KW-ARBITER-005 for the pay-down bar."
    )


def _print_section(label: str, block: dict[str, Any]) -> None:
    click.echo(f"  {label}:")
    pp = block.get("per_principle", {})
    if not pp:
        click.echo("    (no principles triggered)")
    for pid in sorted(pp.keys()):
        s = pp[pid]
        click.echo(
            f"    p={pid:<4} support={s['support']:>3} "
            f"tp={s['tp']:>3} fp={s['fp']:>3} fn={s['fn']:>3} "
            f"wrong_principle={s['wrong_principle']:>3} "
            f"precision={_fmt(s['precision'])} recall={_fmt(s['recall'])}"
        )
    summ = block.get("summary", {})
    if summ:
        click.echo(
            f"    summary: micro_precision={_fmt(summ.get('micro_precision'))} "
            f"micro_recall={_fmt(summ.get('micro_recall'))} "
            f"(tp={summ.get('tp_total', 0)}, fp={summ.get('fp_total', 0)}, "
            f"fn={summ.get('fn_total', 0)}, wrong_principle={summ.get('wrong_principle_total', 0)})"
        )


def _fmt(x: float | None) -> str:
    if x is None:
        return "n/a"
    return f"{x:.4f}"
