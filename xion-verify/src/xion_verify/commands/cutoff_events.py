"""`xion-verify cutoff-events` — anonymized session cutoff audit."""

from __future__ import annotations

import sys

import click

from xion_verify.exit_codes import FAIL, NOT_YET_SEALED, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root

_LEDGER = "ledgers/CUTOFF_EVENTS_LEDGER.jsonl"


@click.command(name="cutoff-events", help="Anonymized cutoff-events audit.")
def cutoff_events() -> None:
    try:
        repo_root = find_repo_root()
        from orchestrator.relay.cutoff_events import verify_cutoff_chain

        count, tip = verify_cutoff_chain(repo_root / _LEDGER)
    except RepoRootNotFound as exc:
        click.echo(f"cutoff-events: FAIL: {exc}", err=True)
        sys.exit(FAIL)
    except Exception as exc:
        click.echo(f"cutoff-events: FAIL: {exc}", err=True)
        sys.exit(FAIL)
    if count == 0:
        click.echo(f"cutoff-events: NOT_YET_SEALED — {_LEDGER} contains no rows")
        sys.exit(NOT_YET_SEALED)
    click.echo(f"cutoff-events: OK (rows={count} tip={tip})")
    sys.exit(OK)


__all__ = ["cutoff_events"]
