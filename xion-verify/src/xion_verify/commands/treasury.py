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
        path = repo_root / rel
        if not path.is_file():
            errors.append(f"missing treasury contract: {rel}")
            continue
        source = path.read_text(encoding="utf-8")
        if rel.endswith("MasterTreasury.sol"):
            for needle in ("function aggregateTotals", "function requestReplenish", "event ReplenishRequested"):
                if needle not in source:
                    errors.append(f"MasterTreasury.sol missing {needle}")
        if rel.endswith("Vault.sol"):
            for needle in ("SafeERC20", "function balanceOf", "function withdraw", "receive() external payable"):
                if needle not in source:
                    errors.append(f"Vault.sol missing {needle}")
    manifest_path = repo_root / manifest_rel
    if not manifest_path.is_file():
        errors.append(f"missing treasury manifest: {manifest_rel}")
        return errors
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        errors.append("treasury manifest schema_version must be 1")
    audit_tx = data.get("treasury_audit_arweave_tx")
    if audit_tx:
        corr = data.get("treasury_audit_correction_arweave_tx")
        if not isinstance(corr, str) or len(corr.strip()) == 0:
            errors.append(
                "treasury_audit_arweave_tx is set but treasury_audit_correction_arweave_tx is missing "
                "(required per docs/audits/treasury-2026-report.CORRECTION.md / KW-AUDIT-002)"
            )
    cap = data.get("bridge_exposure_cap_bps")
    if not isinstance(cap, int) or not 0 <= cap <= 10_000:
        errors.append("bridge_exposure_cap_bps must be integer in [0, 10000]")
    vaults = data.get("vaults")
    if not isinstance(vaults, list):
        errors.append("vaults must be a list")
    tier1 = data.get("tier1_operating_tokens")
    if not isinstance(tier1, list):
        errors.append("tier1_operating_tokens must be a list")
    else:
        assets = {row.get("asset") for row in tier1 if isinstance(row, dict)}
        for required in {"AR", "USDC", "ETH", "TAO"}:
            if required not in assets:
                errors.append(f"tier1_operating_tokens missing {required}")
        if "AKT" in assets:
            errors.append("AKT must not be Tier 1 while Akash is standby blueprint only")
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
    click.echo("treasury: OK (custody/accounting contracts and manifest structure verified; deployment residual remains explicit)")
    sys.exit(OK)


__all__ = ["check_treasury", "treasury"]
