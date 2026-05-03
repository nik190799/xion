"""`xion-verify akash-deploy-discipline` — Akash escrow discipline shape check."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from xion_verify.exit_codes import FAIL, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root


@click.command(
    name="akash-deploy-discipline",
    help="Verify Akash deployer has pre-accept ingress discipline and a provider allowlist.",
)
def akash_deploy_discipline() -> None:
    try:
        repo_root = find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"akash-deploy-discipline: FAIL: {exc}", err=True)
        sys.exit(FAIL)
    errors = evaluate(repo_root)
    if errors:
        for error in errors:
            click.echo(f"akash-deploy-discipline: FAIL: {error}", err=True)
        sys.exit(FAIL)
    click.echo("akash-deploy-discipline: OK (pre-accept provider ingress guard and allowlist present)")
    sys.exit(OK)


def evaluate(repo_root: Path) -> list[str]:
    errors: list[str] = []
    source_path = repo_root / "xion_ops" / "services" / "akash.py"
    allowlist_path = repo_root / "genesis" / "PROVIDER_ALLOWLIST.json"
    if not source_path.is_file():
        return ["missing xion_ops/services/akash.py"]
    source = source_path.read_text(encoding="utf-8")
    for needle in (
        "provider_allowlist",
        "_choose_reachable_provider",
        "_provider_ingress_reachable",
        "pre_accept_reachable",
        "skip_unreachable_provider_ingress",
    ):
        if needle not in source:
            errors.append(f"AkashService missing deploy discipline marker: {needle}")
    if not allowlist_path.is_file():
        errors.append("missing genesis/PROVIDER_ALLOWLIST.json")
    else:
        try:
            payload = json.loads(allowlist_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"invalid provider allowlist JSON: {exc}")
        else:
            providers = payload.get("providers")
            if not isinstance(providers, list) or not providers:
                errors.append("provider allowlist must contain at least one provider")
            elif not all(isinstance(item, dict) and item.get("provider") for item in providers):
                errors.append("every provider allowlist row must include provider")
    return errors


__all__ = ["akash_deploy_discipline", "evaluate"]
