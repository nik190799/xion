"""`xion-verify sustainability` — Cost-Pressure Ladder readout."""

from __future__ import annotations

import math
import sys

import click

from xion_verify.exit_codes import FAIL, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root


@click.command(name="sustainability", help="Composite Cost-Pressure Ladder readout.")
def sustainability() -> None:
    try:
        find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"sustainability: FAIL: {exc}", err=True)
        sys.exit(FAIL)
    try:
        from orchestrator.api.sustainability import sustainability_readout

        readout = sustainability_readout()
    except Exception as exc:
        click.echo(f"sustainability: FAIL: {exc}", err=True)
        sys.exit(FAIL)
    required = (
        "runway_weeks",
        "fraction_of_operating_float",
        "fraction_of_improvement_fund",
        "distance_to_reserve_floor",
        "recurring_burn_ratio",
    )
    for key in required:
        value = readout.get(key)
        if not isinstance(value, (int, float)) or math.isnan(float(value)):
            click.echo(f"sustainability: FAIL: {key} must be numeric", err=True)
            sys.exit(FAIL)
    click.echo(
        "sustainability: OK "
        f"(runway_weeks={readout['runway_weeks']} recurring_burn_ratio={readout['recurring_burn_ratio']})"
    )
    sys.exit(OK)


__all__ = ["sustainability"]
