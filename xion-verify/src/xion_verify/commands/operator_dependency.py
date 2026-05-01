"""`xion-verify operator-dependency` — Operator-Dependency Score readout vs Abdication Schedule.

Promoted to FAIL (not flag) on cloudflare-in-CRITICAL.
"""

from __future__ import annotations

import sys

import click

from xion_verify.exit_codes import FAIL, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root


@click.command(
    name="operator-dependency",
    help="Operator-Dependency Score readout vs Abdication Schedule.",
)
def operator_dependency() -> None:
    try:
        repo_root = find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"operator-dependency: FAIL: {exc}", err=True)
        sys.exit(FAIL)

    abdication_file = repo_root / "docs" / "ABDICATION.md"
    if not abdication_file.is_file():
        click.echo("operator-dependency: FAIL: docs/ABDICATION.md not found", err=True)
        sys.exit(FAIL)

    content = abdication_file.read_text(encoding="utf-8")

    # Parse the table to find Cloudflare and GitHub
    github_found = False
    for line in content.splitlines():
        if "Cloudflare" in line and "CRITICAL" in line:
            click.echo("operator-dependency: FAIL: Cloudflare is listed as CRITICAL", err=True)
            sys.exit(FAIL)
        if "GitHub repository ownership" in line:
            github_found = True
            if "CRITICAL" in line:
                click.echo("operator-dependency: FAIL: GitHub repository ownership is listed as CRITICAL (should be DEGRADED)", err=True)
                sys.exit(FAIL)

    if not github_found:
        click.echo("operator-dependency: FAIL: GitHub repository ownership not found in ABDICATION.md", err=True)
        sys.exit(FAIL)

    click.echo("operator-dependency: OK (Operator-Dependency Score verified)")
    sys.exit(OK)
