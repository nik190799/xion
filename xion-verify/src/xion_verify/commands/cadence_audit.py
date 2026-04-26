"""`xion-verify cadence-audit` — static governance cadence checks."""

from __future__ import annotations

import sys

import click

from xion_verify.exit_codes import FAIL, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root

_MARKERS = (
    ("docs/09-GOVERNANCE.md", "14 days"),
    ("docs/09-GOVERNANCE.md", "Cold Root"),
    ("docs/13-OPERATIONS.md", "Cold Root"),
    ("docs/ABDICATION.md", "No milestone may be delayed"),
)


@click.command(name="cadence-audit", help="Verify governance and Rite minimum-window cadence markers.")
def cadence_audit() -> None:
    try:
        repo_root = find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"cadence-audit: FAIL: {exc}", err=True)
        sys.exit(FAIL)
    for rel, marker in _MARKERS:
        path = repo_root / rel
        if not path.is_file():
            click.echo(f"cadence-audit: FAIL: missing {rel}", err=True)
            sys.exit(FAIL)
        if marker not in path.read_text(encoding="utf-8"):
            click.echo(f"cadence-audit: FAIL: {rel} missing marker {marker!r}", err=True)
            sys.exit(FAIL)
    click.echo("cadence-audit: OK (minimum governance cadence markers present)")
    sys.exit(OK)


__all__ = ["cadence_audit"]
