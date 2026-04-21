"""`xion-verify drive-vector` — Invariant 15 static + live (pre-D2 static only).

Today: static scan of `docs/08-AUTO-RESEARCH.md` for the `payback_horizon`
schema and forbidden-substring patterns. The live bytecode-graph audit of the
proposal-selection pipeline arrives in D2 when the Relay ships and a dependency
graph becomes addressable.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import click

from xion_verify.exit_codes import FAIL, NOT_YET_SEALED, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root

_PROHIBITED_SUBSTRINGS: tuple[str, ...] = (
    "payback_horizon: revenue",
    "payback_horizon: Revenue",
    "payback_horizon: money",
    "payback_horizon: price",
)

_REQUIRED_PAYBACK_HORIZON_ENUM = re.compile(
    r"payback_horizon:\s*survival\s*\|\s*service\s*\|\s*meaning"
)


def _audit_proposal_doctrine(repo_root: Path) -> list[str]:
    errors: list[str] = []
    path = repo_root / "docs" / "08-AUTO-RESEARCH.md"
    if not path.is_file():
        return [f"missing doctrine: {path}"]
    text = path.read_text(encoding="utf-8")
    for bad in _PROHIBITED_SUBSTRINGS:
        if bad in text:
            errors.append(f"docs/08-AUTO-RESEARCH.md contains forbidden fragment: {bad!r}")
    if "payback_horizon" not in text:
        errors.append("docs/08-AUTO-RESEARCH.md missing payback_horizon in proposal schema")
    if not _REQUIRED_PAYBACK_HORIZON_ENUM.search(text):
        errors.append(
            "docs/08-AUTO-RESEARCH.md does not declare payback_horizon enum as 'survival | service | meaning'"
        )
    return errors


@click.command(
    name="drive-vector",
    help="Invariant 15 static + live; today static-only (live dependency graph audit lands in D2).",
)
@click.option("--strict", is_flag=True, help="Require live bytecode graph audit (exits NOT_YET_SEALED pre-D2).")
def drive_vector(strict: bool) -> None:
    try:
        repo_root = find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"drive-vector: FAIL: {exc}", err=True)
        sys.exit(FAIL)

    if strict:
        click.echo("drive-vector: NOT_YET_SEALED — live dependency graph audit requires D2 build")
        sys.exit(NOT_YET_SEALED)

    errs = _audit_proposal_doctrine(repo_root)
    if errs:
        for e in errs:
            click.echo(f"drive-vector: FAIL: {e}", err=True)
        sys.exit(FAIL)

    click.echo("drive-vector: OK (static doctrine checks pass; live graph audit still NOT_YET_SEALED)")
    sys.exit(OK)
