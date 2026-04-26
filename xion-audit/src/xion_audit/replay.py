"""`xion-audit replay` — re-run a v2 provider against a SAFETY_LEDGER row
and honestly report where it reproduced and where it drifted.

Per [`docs/04-ARCHITECTURE.md`](../../../docs/04-ARCHITECTURE.md) § "Auditor replay":
an auditor replaying a row with `llm_verdict.provider_id ==
"chutes-llm-judge"` must:

1. Obtain the candidate out-of-band (the ledger never stores it).
2. Re-post to the provider.
3. Serialise the structured judge JSON canonically.
4. Compare `sha256(canonical)` against the row's
   `llm_verdict.raw_output_sha256`. **Byte-equal match is the
   strong property.** What MUST reproduce in every case are the
   `decision` and `principle_id`.

This module implements that procedure and prints four honest signals:

* **sha256 match.** Byte-identical canonical output.
* **decision match.** Does the provider `decision` reproduce? (OK /
  REFUSE / ESCALATE.)
* **principle_id match.** Does the provider Covenant principle id
  reproduce? **This is the strong property the doctrine pins.**
* **confidence.** Replay-side confidence from the structured judge JSON.

Exit codes:
  0 — principle_id + decision reproduced (sha may or may not match).
  1 — principle_id or decision drifted. Row is suspect; see output.
  2 — NOT_YET_SEALED: XION_CHUTES_API_KEY not set, or row points at a
      provider we cannot replay from this tool (non-chutes-llm-judge,
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
    from orchestrator.safety.providers.chutes_llm_judge import ChutesLlmJudgeProvider

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

    if str(llm.get("provider_id")) != "chutes-llm-judge":
        click.echo(
            f"replay: NOT_YET_SEALED: row seq={seq} provider_id="
            f"{llm.get('provider_id')!r}; this tool only replays chutes-llm-judge.",
            err=True,
        )
        raise SystemExit(2)

    if not os.environ.get("XION_CHUTES_API_KEY", "").strip():
        click.echo(
            "replay: NOT_YET_SEALED: XION_CHUTES_API_KEY not set; cannot re-call provider. "
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
    p = ChutesLlmJudgeProvider()
    judgement = p.judge(candidate_text)

    replay_raw_bytes = bytes(judgement.raw_output)
    replay_sha = hashlib.sha256(replay_raw_bytes).hexdigest()

    replay_canonical: dict[str, Any] = json.loads(replay_raw_bytes.decode("utf-8"))
    replay_decision = judgement.decision.value
    replay_principle = judgement.principle_id

    # ------------------------------------------------------------- signals
    sha_match = (replay_sha == expected_sha) if expected_sha else False
    decision_match = (replay_decision == expected_decision)
    principle_match = (replay_principle == expected_principle)
    provider_version_match = (int(judgement.provider_version) == expected_version)

    report: dict[str, Any] = {
        "ledger_path": str(ledger_path),
        "seq": int(seq),
        "provider_id": "chutes-llm-judge",
        "provider_version_expected": expected_version,
        "provider_version_replay": int(judgement.provider_version),
        "provider_version_match": provider_version_match,
        "raw_output_sha256_expected": expected_sha,
        "raw_output_sha256_replay": replay_sha,
        "raw_output_sha256_match": sha_match,
        "decision_expected": expected_decision,
        "decision_replay": replay_decision,
        "decision_match": decision_match,
        "principle_id_expected": expected_principle,
        "principle_id_replay": replay_principle,
        "principle_id_match": principle_match,
        "replay_confidence": judgement.confidence,
        "replay_raw_output": replay_canonical,
    }

    if json_out:
        click.echo(json.dumps(report, sort_keys=True, indent=2))
    else:
        click.echo(
            f"replay: seq={seq} provider=chutes-llm-judge v{expected_version}"
            f"{' (provider version drift!)' if not provider_version_match else ''}"
        )
        click.echo(f"  raw_output_sha256: "
                   f"{'MATCH' if sha_match else 'DRIFT (see decision + principle_id)'}")
        click.echo(f"    expected: {expected_sha}")
        click.echo(f"    replay:   {replay_sha}")
        click.echo(f"  decision:      {'MATCH' if decision_match else 'DRIFT'}  "
                   f"expected={expected_decision!r}  replay={replay_decision!r}")
        click.echo(f"  principle_id:  {'MATCH' if principle_match else 'DRIFT'}  "
                   f"expected={expected_principle!r}  replay={replay_principle!r}")
        click.echo(f"  replay confidence={judgement.confidence:.4f}")

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
