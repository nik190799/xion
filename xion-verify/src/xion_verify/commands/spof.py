"""`xion-verify spof` — single-point-of-failure topology check."""

from __future__ import annotations

import sys

import click

from xion_verify.exit_codes import FAIL, OK
from xion_verify.repo import find_repo_root


@click.command(name="spof", help="Enumerate single points of failure; fail on constitutional-tier SPOFs.")
def spof() -> None:
    try:
        repo_root = find_repo_root()
        from orchestrator.topology import dependency_report

        report = dependency_report(repo_root)
    except Exception as exc:
        click.echo(f"spof: FAIL: {exc}", err=True)
        sys.exit(FAIL)
    bad = [
        dep["name"]
        for dep in report.get("dependencies", [])
        if dep.get("tier") == "constitutional" and not dep.get("redundancy")
    ]
    if bad:
        click.echo(f"spof: FAIL: constitutional-tier SPOFs: {bad}", err=True)
        sys.exit(FAIL)
    artifacts = report.get("artifacts", {})
    if not all(artifacts.values()):
        click.echo(f"spof: FAIL: missing topology artifacts {artifacts}", err=True)
        sys.exit(FAIL)
    click.echo(f"spof: OK ({len(report.get('dependencies', []))} dependencies enumerated)")
    sys.exit(OK)


__all__ = ["spof"]
