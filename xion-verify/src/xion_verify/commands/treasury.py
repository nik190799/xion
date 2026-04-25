"""`xion-verify treasury` — structural treasury-vault posture."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from xion_verify.exit_codes import FAIL, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root

_MANIFEST = "genesis/TREASURY_VAULTS.json"
_CONTRACTS = ("contracts/treasury/MasterTreasury.sol", "contracts/treasury/Vault.sol")


def check_treasury(repo_root: Path, manifest_rel: str = _MANIFEST) -> list[str]:
    errors: list[str] = []
    for rel in _CONTRACTS:
        if not (repo_root / rel).is_file():
            errors.append(f"missing treasury contract: {rel}")
    manifest_path = repo_root / manifest_rel
    if not manifest_path.is_file():
        errors.append(f"missing treasury manifest: {manifest_rel}")
        return errors
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        errors.append("treasury manifest schema_version must be 1")
    cap = data.get("bridge_exposure_cap_bps")
    if not isinstance(cap, int) or not 0 <= cap <= 10_000:
        errors.append("bridge_exposure_cap_bps must be integer in [0, 10000]")
    vaults = data.get("vaults")
    if not isinstance(vaults, list):
        errors.append("vaults must be a list")
    return errors


@click.command(name="treasury", help="Verify treasury vault contract and manifest structure.")
def treasury() -> None:
    try:
        repo_root = find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"treasury: FAIL: {exc}", err=True)
        sys.exit(FAIL)
    errors = check_treasury(repo_root)
    if errors:
        for error in errors:
            click.echo(f"treasury: FAIL: {error}", err=True)
        sys.exit(FAIL)
    click.echo("treasury: OK (treasury contracts and manifest structure verified; deployment residual remains explicit)")
    sys.exit(OK)


__all__ = ["check_treasury", "treasury"]
