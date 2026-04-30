"""Deployment-aware contract verifiers for D3."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from orchestrator.treasury import SettlementChainSettings, get_settlement_chain

from xion_verify.exit_codes import FAIL, NOT_YET_SEALED, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root

_MANIFEST = "genesis/CONTRACT_ADDRESSES.json"


def _load_manifest(repo_root: Path) -> tuple[int, dict[str, object] | str]:
    path = repo_root / _MANIFEST
    if not path.is_file():
        return NOT_YET_SEALED, f"{_MANIFEST} not found"
    try:
        chain = get_settlement_chain(
            SettlementChainSettings(chain="base", repo_root=repo_root)
        )
        return OK, chain.authorities_root()
    except (OSError, json.JSONDecodeError, RuntimeError) as exc:
        return NOT_YET_SEALED, str(exc)


def _command(label: str, fields: tuple[str, ...]) -> None:
    try:
        repo_root = find_repo_root()
        code, result = _load_manifest(repo_root)
    except (RepoRootNotFound, OSError, json.JSONDecodeError) as exc:
        click.echo(f"{label}: FAIL: {exc}", err=True)
        sys.exit(FAIL)
    if code != OK:
        click.echo(f"{label}: NOT_YET_SEALED — {result}")
        sys.exit(code)
    manifest = result  # type: ignore[assignment]
    missing = [field for field in fields if not manifest.get(field)]
    if missing:
        click.echo(f"{label}: FAIL: missing deployed fields {missing}", err=True)
        sys.exit(FAIL)
    click.echo(f"{label}: OK (Base Sepolia deployment manifest populated)")
    sys.exit(OK)


@click.command(name="supply", help="Verify XION total supply and genesis split deployment manifest.")
def supply() -> None:
    _command("supply", ("xion_token", "emission_controller"))


@click.command(name="liquidity-lock", help="Verify LiquidityLock deployment manifest.")
def liquidity_lock() -> None:
    _command("liquidity-lock", ("liquidity_lock",))


@click.command(name="authorities", help="Verify authority-contract deployment manifest.")
def authorities() -> None:
    _command("authorities", ("xion_token", "imprint", "emission_controller", "liquidity_lock"))


__all__ = ["authorities", "liquidity_lock", "supply"]
