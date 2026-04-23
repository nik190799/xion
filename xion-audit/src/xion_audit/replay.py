"""`xion-audit replay` — re-run a v2 provider against a SAFETY_LEDGER row
and honestly report where it reproduced and where it drifted.

Per [`docs/04-ARCHITECTURE.md`](../../../docs/04-ARCHITECTURE.md) § "Auditor replay":
an auditor replaying a row with `llm_verdict.provider_id ==
"openai-moderation"` must:

1. Obtain the candidate out-of-band (the ledger never stores it).
2. Re-post to the provider.
3. Strip `id`, serialise `{model, results}` canonically.
4. Compare `sha256(canonical)` against the row's
   `llm_verdict.raw_output_sha256`. **Byte-equal match is the
   strong property; score-drift mismatches are expected and do not
   invalidate the row.** What MUST reproduce in every case are the
   `flagged` booleans and the `principle_id` the mapping table
   would have produced.

This module implements that procedure and prints four honest signals:

* **sha256 match.** Byte-identical canonical output. Usually false in
  practice (OpenAI GPU scoring drifts ~1e-6).
* **decision match.** Does the mapped `decision` reproduce? (OK /
  REFUSE / ESCALATE.)
* **principle_id match.** Does the mapped Covenant principle id
  reproduce? **This is the strong property the doctrine pins.**
* **score drift.** Max abs delta between the replay's
  `category_scores` and the ledger row's reconstructable scores —
  informational only; the ledger stores only the sha256, not the
  scores, so we derive the best signal we can from the replay side
  alone.

Exit codes:
  0 — principle_id + decision reproduced (sha may or may not match).
  1 — principle_id or decision drifted. Row is suspect; see output.
  2 — NOT_YET_SEALED: OPENAI_API_KEY not set, or row points at a
      provider we cannot replay from this tool (non-openai-moderation,
      or a v1 `principle_id`-only row with no `llm_verdict`).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import click

from xion_audit.repo import find_repo_root_or_cwd


@click.command("replay")
@click.option(
    "--ledger",
    "ledger_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Path to SAFETY_LEDGER.jsonl (auditor's copy).",
)
@click.option(
    "--seq",
    "seq",
    type=int,
    required=True,
    help="`seq` field of the row to replay.",
)
@click.option(
    "--candidate-file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="UTF-8 file containing the exact candidate bytes the row was produced from (obtained out-of-band).",
)
@click.option(
    "--json",
    "json_out",
    is_flag=True,
    help="Emit a single JSON object on stdout instead of the human-readable report.",
)
def replay(ledger_path: Path, seq: int, candidate_file: Path, json_out: bool) -> None:
    import os

    from orchestrator.safety.ledger import iter_rows
    from orchestrator.safety.providers.openai_moderation import (
        OpenAIModerationProvider,
        _asymmetric_when_unflagged,
        _select_principle,
    )

    try:
        find_repo_root_or_cwd()
    except FileNotFoundError as e:
        click.echo(f"replay: FAIL: {e}", err=True)
        raise SystemExit(1) from e

    # ---------------------------------------------------------------- ledger
    row: dict[str, Any] | None = None
    for r in iter_rows(ledger_path):
        if int(r.get("seq", -1)) == int(seq):
            row = r
            break
    if row is None:
        click.echo(f"replay: FAIL: no row with seq={seq} in {ledger_path}", err=True)
        raise SystemExit(1)

    llm = row.get("llm_verdict")
    if not isinstance(llm, dict):
        click.echo(
            f"replay: NOT_YET_SEALED: row seq={seq} has no llm_verdict "
            "(v1-only row, or v2 did not run). Nothing to replay.",
            err=True,
        )
        raise SystemExit(2)

    if str(llm.get("provider_id")) != "openai-moderation":
        click.echo(
            f"replay: NOT_YET_SEALED: row seq={seq} provider_id="
            f"{llm.get('provider_id')!r}; this tool only replays openai-moderation.",
            err=True,
        )
        raise SystemExit(2)

    if not os.environ.get("OPENAI_API_KEY", "").strip():
        click.echo(
            "replay: NOT_YET_SEALED: OPENAI_API_KEY not set; cannot re-call provider. "
            "Export the key and re-run.",
            err=True,
        )
        raise SystemExit(2)

    expected_sha = str(llm.get("raw_output_sha256", ""))
    expected_version = int(llm.get("provider_version", 0))
    expected_decision = str(llm.get("decision", ""))
    expected_principle = llm.get("principle_id")

    # -------------------------------------------------------------- candidate
    # Integrity: the ledger row pins candidate_sha256. If the auditor's
    # copy of the text doesn't match, we bail before burning an API call.
    candidate_bytes = candidate_file.read_bytes()
    candidate_text = candidate_bytes.decode("utf-8")
    got_candidate_sha = hashlib.sha256(candidate_text.encode("utf-8")).hexdigest()
    expected_candidate_sha = str(row.get("candidate_sha256", ""))
    if expected_candidate_sha and got_candidate_sha != expected_candidate_sha:
        click.echo(
            f"replay: FAIL: candidate file sha256={got_candidate_sha} does not "
            f"match row candidate_sha256={expected_candidate_sha}. The auditor's "
            "out-of-band candidate is not the one the ledger row saw. Do not replay.",
            err=True,
        )
        raise SystemExit(1)

    # -------------------------------------------------------------- replay call
    p = OpenAIModerationProvider()
    judgement = p.judge(candidate_text)

    # Re-materialise the parsed response from the provider via the same
    # canonical projection used at write time. We don't have the raw
    # response bytes here (judge() consumes them), but _canonical_raw_output
    # is implicitly what judgement.raw_output already is.
    replay_raw_bytes = bytes(judgement.raw_output)
    replay_sha = hashlib.sha256(replay_raw_bytes).hexdigest()

    # Pull flagged categories + scores from the replay's raw_output for
    # the table-reapplication check (the strong doctrine property).
    replay_canonical: dict[str, Any] = json.loads(replay_raw_bytes.decode("utf-8"))
    results = replay_canonical.get("results") or []
    if not results:
        click.echo("replay: FAIL: replay raw_output missing results[]", err=True)
        raise SystemExit(1)
    r0 = results[0]
    flagged_bool = bool(r0.get("flagged", False))
    categories: dict[str, bool] = r0.get("categories") or {}
    category_scores: dict[str, float] = r0.get("category_scores") or {}

    # Apply the category→principle table to the replay side. This is the
    # doctrine-pinned strong property: the flagged/asymmetric mapping
    # MUST reproduce independent of score drift.
    table_decision: str
    table_principle: str | None
    if flagged_bool:
        try:
            dec_enum, prin, _all = _select_principle(categories, category_scores)
            table_decision = dec_enum.value
            table_principle = prin
        except ValueError:
            table_decision = "escalate"  # fail-closed, per doctrine
            table_principle = None
    else:
        asym = _asymmetric_when_unflagged(categories, category_scores)
        if asym is None:
            table_decision = "ok"
            table_principle = None
        else:
            dec_enum, prin, _summary = asym
            table_decision = dec_enum.value
            table_principle = prin

    # ------------------------------------------------------------- signals
    sha_match = (replay_sha == expected_sha) if expected_sha else False
    decision_match = (table_decision == expected_decision)
    principle_match = (table_principle == expected_principle)
    provider_version_match = (int(judgement.provider_version) == expected_version)

    # Best-effort score-drift signal. We cannot compare against the row
    # (the ledger stores only the sha256), so we emit the largest score
    # the replay observed so an auditor can eyeball whether the
    # no-match is "nearly the same" or "radically different".
    top_score = 0.0
    if category_scores:
        try:
            top_score = float(max(category_scores.values()))
        except (TypeError, ValueError):
            top_score = 0.0

    report: dict[str, Any] = {
        "ledger_path": str(ledger_path),
        "seq": int(seq),
        "provider_id": "openai-moderation",
        "provider_version_expected": expected_version,
        "provider_version_replay": int(judgement.provider_version),
        "provider_version_match": provider_version_match,
        "raw_output_sha256_expected": expected_sha,
        "raw_output_sha256_replay": replay_sha,
        "raw_output_sha256_match": sha_match,
        "decision_expected": expected_decision,
        "decision_replay_from_table": table_decision,
        "decision_match": decision_match,
        "principle_id_expected": expected_principle,
        "principle_id_replay_from_table": table_principle,
        "principle_id_match": principle_match,
        "replay_flagged": flagged_bool,
        "replay_top_category_score": top_score,
        "replay_flagged_categories": sorted(c for c, on in categories.items() if on),
    }

    if json_out:
        click.echo(json.dumps(report, sort_keys=True, indent=2))
    else:
        click.echo(
            f"replay: seq={seq} provider=openai-moderation v{expected_version}"
            f"{' (provider version drift!)' if not provider_version_match else ''}"
        )
        click.echo(f"  raw_output_sha256: "
                   f"{'MATCH' if sha_match else 'DRIFT (score-drift is expected; see principle_id)'}")
        click.echo(f"    expected: {expected_sha}")
        click.echo(f"    replay:   {replay_sha}")
        click.echo(f"  decision:      {'MATCH' if decision_match else 'DRIFT'}  "
                   f"expected={expected_decision!r}  replay={table_decision!r}")
        click.echo(f"  principle_id:  {'MATCH' if principle_match else 'DRIFT'}  "
                   f"expected={expected_principle!r}  replay={table_principle!r}")
        click.echo(f"  replay flagged={flagged_bool} "
                   f"top_category_score={top_score:.4f} "
                   f"flagged_categories={report['replay_flagged_categories']}")

    if not decision_match or not principle_match:
        # Strong property failed. Row is suspect. Exit 1; the operator
        # investigates (provider drift? category map needs an update?
        # ledger tampered?).
        if not json_out:
            click.echo(
                "replay: FAIL: decision or principle_id did not reproduce. "
                "Doctrine-pinned strong property is violated; investigate.",
                err=True,
            )
        raise SystemExit(1)

    if not json_out:
        click.echo(
            "replay: OK  doctrine-pinned strong property reproduced "
            "(decision + principle_id match); sha256 drift is expected."
        )
    raise SystemExit(0)
