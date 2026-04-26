"""`xion-verify crypto-currency` — active crypto-policy check."""

from __future__ import annotations

import sys

import click

from xion_verify.exit_codes import FAIL, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root


@click.command(name="crypto-currency", help="Verify active crypto_policy_vN matches the Cryptoception feed.")
def crypto_currency() -> None:
    try:
        repo_root = find_repo_root()
        from orchestrator.cryptoception import active_crypto_policy

        policy = active_crypto_policy(repo_root)
    except (RepoRootNotFound, OSError, ValueError) as exc:
        click.echo(f"crypto-currency: FAIL: {exc}", err=True)
        sys.exit(FAIL)
    if policy.get("schema_version") != 1 or policy.get("policy_id") != "crypto_policy_v1":
        click.echo("crypto-currency: FAIL: unexpected crypto policy identity", err=True)
        sys.exit(FAIL)
    if policy.get("hash_algorithm") != "sha256":
        click.echo("crypto-currency: FAIL: hash_algorithm must be sha256 in v1", err=True)
        sys.exit(FAIL)
    if "ed25519" not in policy.get("signature_algorithms", []):
        click.echo("crypto-currency: FAIL: ed25519 signature algorithm missing", err=True)
        sys.exit(FAIL)
    click.echo("crypto-currency: OK (crypto_policy_v1 feed matches genesis default)")
    sys.exit(OK)


__all__ = ["crypto_currency"]
