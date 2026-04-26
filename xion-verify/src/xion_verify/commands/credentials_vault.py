"""`xion-verify credentials-vault` — public credentials-vault posture."""

from __future__ import annotations

import sys

import click

from xion_verify.exit_codes import FAIL, OK
from xion_verify.repo import find_repo_root


@click.command(name="credentials-vault", help="Verify Credentials vault posture.")
def credentials_vault() -> None:
    try:
        repo_root = find_repo_root()
        from orchestrator.credentials import load_vault_posture

        posture = load_vault_posture(repo_root)
    except Exception as exc:
        click.echo(f"credentials-vault: FAIL: {exc}", err=True)
        sys.exit(FAIL)
    threshold = posture.get("threshold", {})
    if posture.get("schema_version") != 1 or posture.get("sealed_at_rest") is not True:
        click.echo("credentials-vault: FAIL: vault must be schema v1 and sealed_at_rest=true", err=True)
        sys.exit(FAIL)
    if threshold.get("k", 0) < 2 or threshold.get("n", 0) < threshold.get("k", 0):
        click.echo("credentials-vault: FAIL: threshold must be k-of-n with k>=2 and n>=k", err=True)
        sys.exit(FAIL)
    log_rel = posture.get("rotation_log")
    if not isinstance(log_rel, str) or not (repo_root / log_rel).is_file():
        click.echo("credentials-vault: FAIL: rotation_log missing", err=True)
        sys.exit(FAIL)
    click.echo(
        f"credentials-vault: OK (sealed_at_rest=true threshold={threshold.get('k')}-of-{threshold.get('n')})"
    )
    sys.exit(OK)


__all__ = ["credentials_vault"]
