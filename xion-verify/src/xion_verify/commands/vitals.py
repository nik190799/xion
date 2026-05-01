"""`xion-verify vitals` — composite 8-domain vital-signs readout.

Returns OK or honest NOT_YET_SEALED per domain.
"""

from __future__ import annotations

import sys

import click

from xion_verify.exit_codes import FAIL, NOT_YET_SEALED, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root


@click.command(
    name="vitals",
    help="Composite 8-domain vital-signs readout with methodology hashes.",
)
def vitals() -> None:
    try:
        repo_root = find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"vitals: FAIL: {exc}", err=True)
        sys.exit(FAIL)

    sys.path.insert(0, str(repo_root))
    try:
        from orchestrator.vitals import get_composite_vitals
    except ImportError as e:
        click.echo(f"vitals: FAIL: Could not import orchestrator.vitals: {e}", err=True)
        sys.exit(FAIL)

    domains = get_composite_vitals()
    all_ok = True
    all_not_yet_sealed = True

    click.echo("--- Vital Signs ---")
    for d in domains:
        if d.band == "not_yet_sealed":
            click.echo(f"  {d.name}: NOT_YET_SEALED")
            all_ok = False
        else:
            click.echo(f"  {d.name}: {d.band.upper()} (reading: {d.reading})")
            all_not_yet_sealed = False

    if all_not_yet_sealed:
        click.echo("vitals: NOT_YET_SEALED — All domains are NOT_YET_SEALED")
        sys.exit(NOT_YET_SEALED)

    if not all_ok:
        # If some are OK and some are NOT_YET_SEALED, we return NOT_YET_SEALED
        # so the overall `xion-verify all` knows it's not fully sealed.
        click.echo("vitals: NOT_YET_SEALED — Some domains are NOT_YET_SEALED")
        sys.exit(NOT_YET_SEALED)

    click.echo("vitals: OK")
    sys.exit(OK)
