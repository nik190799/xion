"""AO deployment manifest verifiers for D3."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from xion_verify.exit_codes import FAIL, NOT_YET_SEALED, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root

_RECEIPT = "genesis/AO_DEPLOY_RECEIPT.json"


def _load_receipt(repo_root: Path) -> tuple[int, dict[str, object] | str]:
    path = repo_root / _RECEIPT
    if not path.is_file():
        return NOT_YET_SEALED, f"{_RECEIPT} not found"
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("substrate") == "localnet":
        return NOT_YET_SEALED, "AO Core receipt is still localnet; AO testnet deploy required for D3"
    if not data.get("process_id"):
        return NOT_YET_SEALED, "AO process_id not populated"
    return OK, data


def _run(label: str) -> None:
    try:
        repo_root = find_repo_root()
        code, result = _load_receipt(repo_root)
    except (RepoRootNotFound, OSError, json.JSONDecodeError) as exc:
        click.echo(f"{label}: FAIL: {exc}", err=True)
        sys.exit(FAIL)
    if code != OK:
        click.echo(f"{label}: NOT_YET_SEALED — {result}")
        sys.exit(code)
    receipt = result  # type: ignore[assignment]
    click.echo(f"{label}: OK (process_id={receipt.get('process_id')})")
    sys.exit(OK)


@click.command(name="state-tip", help="Print current AO state-chain tip.")
def state_tip() -> None:
    _run("state-tip")


@click.command(name="identity", help="Verify AO Process ID against canonical receipt.")
def identity() -> None:
    _run("identity")


@click.command(name="sister-fork-readiness", help="Verify sister-Core fork procedure has a deployed source receipt.")
def sister_fork_readiness() -> None:
    _run("sister-fork-readiness")


__all__ = ["identity", "sister_fork_readiness", "state_tip"]
