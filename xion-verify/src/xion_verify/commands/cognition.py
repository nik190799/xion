"""`xion-verify cognition` — cognition-layer property suite (docs/24-COGNITION.md §11).

Today this subcommand is a pre-D2 stub: it statically confirms the cognition
doctrine exists and declares the live-endpoint checks `NOT_YET_SEALED`. When
the Relay ships in Phase 5 with cognition metrics endpoints, this command
becomes the enforcer of Invariant 6's cognition-layer mechanism row.

Exit contract:
  - default mode: exit 0 (static doctrine checks pass) or 1 (doctrine drift)
  - `--strict`: exit 2 (`NOT_YET_SEALED`) because live metrics aren't wired
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from xion_verify.exit_codes import FAIL, NOT_YET_SEALED, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root

_REQUIRED_DOCTRINE: tuple[tuple[str, str], ...] = (
    ("docs/24-COGNITION.md", "Cognition doctrine"),
    ("genesis/UNKNOWNS.md", "UNKNOWNS companion"),
)


def _static_checks(repo_root: Path) -> list[str]:
    errors: list[str] = []
    for rel, label in _REQUIRED_DOCTRINE:
        if not (repo_root / rel).is_file():
            errors.append(f"{label} missing at {rel}")
    return errors


@click.command(
    name="cognition",
    help="Cognition-layer property suite (strengthens Invariants 2, 6, 7, 15; pre-D2 is static).",
)
@click.option("--strict", is_flag=True, help="Exit NOT_YET_SEALED until Relay metrics endpoints ship (D2).")
@click.option("--bus-audit", is_flag=True, help="Run specialist bus-traffic audit (stub).")
@click.option("--forget-sim", is_flag=True, help="Simulate /forget propagation (stub).")
@click.option("--identity", is_flag=True, help="Identity-hash agreement only (stub).")
def cognition(strict: bool, bus_audit: bool, forget_sim: bool, identity: bool) -> None:
    try:
        repo_root = find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"cognition: FAIL: {exc}", err=True)
        sys.exit(FAIL)

    if strict:
        click.echo("cognition: NOT_YET_SEALED — Relay metrics endpoints not wired (D2)")
        sys.exit(NOT_YET_SEALED)

    errs = _static_checks(repo_root)
    if errs:
        for e in errs:
            click.echo(f"cognition: FAIL: {e}", err=True)
        sys.exit(FAIL)

    click.echo("cognition: OK (static doctrine checks pass; §11 property suite is pre-D2)")
    if bus_audit or forget_sim or identity:
        click.echo("cognition: requested sub-check is stub-only until D2")
    sys.exit(OK)
