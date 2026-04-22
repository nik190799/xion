"""`xion-verify sensorium-ledger` — walk and verify SENSORIUM_LEDGER.

Property promised.

  1. Every row in `SENSORIUM_LEDGER.jsonl` is well-formed against
     `docs/schemas/ledger-sensorium.yaml` schema_version 1.
  2. The hash chain is intact: every row's `prev_hash` matches the
     prior row's `this_hash`, every row's `this_hash` recomputes, and
     `seq` is contiguous starting at 0.
  3. Conditional-field rules hold:
       - distress rows carry `distress_score` and `snapshot_hash=null`
       - tick_commit rows carry `snapshot_hash` and `distress_score=null`
  4. `event_type` and `channel` are members of their respective enums.

On success, prints a per-event-type, per-channel tally so operators
can see at a glance whether distress is being observed at all and
whether the paralinguistic channel has started emitting.

Ledger location. `$XION_SENSORIUM_LEDGER` if set, else
`<repo_root>/SENSORIUM_LEDGER.jsonl`.

Missing or empty ledger. The Sensorium may not have emitted any rows
yet (Phase 5c: the writer exists, but no Relay-side tick loop has
been wired yet; distress rows only land when `gate()`'s distress
consumer is called). A MISSING or empty ledger therefore exits
NOT_YET_SEALED with a specific reason, NOT FAIL — the ledger's
absence is not a constitutional violation, it is a deployment state.
Once rows land, the verifier upgrades to OK/FAIL semantics
automatically.

Cross-ledger join (distress correlation_id -> SAFETY_LEDGER /
REQUEST_LEDGER) is NOT checked today. That lands when gate()'s
distress consumer is wired into live Relay traffic (Phase 5d or later);
documented in `docs/schemas/ledger-sensorium.yaml::verifier_pending`.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import click

from xion_verify.exit_codes import FAIL, NOT_YET_SEALED, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root

_LEDGER_FILENAME = "SENSORIUM_LEDGER.jsonl"


def _default_ledger_path(repo_root: Path) -> Path:
    env = os.environ.get("XION_SENSORIUM_LEDGER")
    if env:
        return Path(env)
    return repo_root / _LEDGER_FILENAME


@click.command(
    name="sensorium-ledger",
    help="Walk SENSORIUM_LEDGER.jsonl; verify schema + chain; report per-event-type tallies (Phase 5c).",
)
@click.option(
    "--path",
    "ledger_override",
    type=click.Path(path_type=Path),
    default=None,
    help="Override the SENSORIUM_LEDGER path (defaults to $XION_SENSORIUM_LEDGER then <repo>/SENSORIUM_LEDGER.jsonl).",
)
def sensorium_ledger(ledger_override: Path | None) -> None:
    try:
        repo_root = find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"sensorium-ledger: FAIL: {exc}", err=True)
        sys.exit(FAIL)

    # Import the orchestrator module lazily — its absence on a sister-Core
    # fork that predates Phase 5c is a real NOT_YET_SEALED condition.
    try:
        from orchestrator.sensorium.ledger import (
            ChainBroken,
            iter_rows,
            tally_by_event_type,
            verify_chain,
        )
    except ImportError as exc:
        click.echo(
            f"sensorium-ledger: NOT_YET_SEALED — orchestrator.sensorium.ledger not importable "
            f"({type(exc).__name__}: {exc}); Phase 5c code surface not present on this fork"
        )
        sys.exit(NOT_YET_SEALED)

    path = ledger_override if ledger_override is not None else _default_ledger_path(repo_root)

    if not path.is_file():
        click.echo(
            f"sensorium-ledger: NOT_YET_SEALED — no ledger at {path}. "
            "The Sensorium writer is live (orchestrator.sensorium.ledger) but no rows have "
            "been emitted yet; once gate()'s distress consumer or a tick loop runs, rows will "
            "land and this verifier will upgrade to OK/FAIL."
        )
        sys.exit(NOT_YET_SEALED)

    # Empty files are treated the same as missing — an honest "no rows
    # yet" state. A zero-byte file is a legal intermediate state between
    # file create and first append.
    row_count = sum(1 for _ in iter_rows(path))
    if row_count == 0:
        click.echo(
            f"sensorium-ledger: NOT_YET_SEALED — ledger at {path} is empty (0 rows). "
            "The file exists but no distress or tick_commit rows have been appended yet."
        )
        sys.exit(NOT_YET_SEALED)

    try:
        count, tip = verify_chain(path)
    except ChainBroken as exc:
        click.echo(f"sensorium-ledger: FAIL: chain broken: {exc}", err=True)
        sys.exit(FAIL)

    tally = tally_by_event_type(path)
    click.echo(
        f"sensorium-ledger: OK (count={count} tip={tip[:16]}... path={path})"
    )
    # Report per-event-type, per-channel so auditors can see distress
    # levels and whether paralinguistic has started emitting.
    for event_type in sorted(tally):
        for channel in sorted(tally[event_type]):
            click.echo(
                f"  event_type={event_type} channel={channel} "
                f"count={tally[event_type][channel]}"
            )
    sys.exit(OK)
