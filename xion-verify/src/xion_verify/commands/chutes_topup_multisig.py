"""Verify Chutes top-up rows carry Spend Authority references."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import click

from xion_verify.exit_codes import FAIL, NOT_YET_SEALED, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root


@click.command(name="chutes-topup-multisig")
@click.option("--ledger", "ledger_path", type=click.Path(path_type=Path), default=None)
def chutes_topup_multisig(ledger_path: Path | None) -> None:
    try:
        repo = find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"chutes-topup-multisig: FAIL: {exc}", err=True)
        sys.exit(FAIL)

    ledger = ledger_path or Path(os.environ.get(
        "XION_CHUTES_BILLING_LEDGER",
        str(repo / "ledgers/BILLING_LEDGER.jsonl"),
    ))
    if not ledger.is_absolute():
        ledger = repo / ledger
    if not ledger.is_file():
        click.echo("chutes-topup-multisig: NOT_YET_SEALED: no BILLING_LEDGER yet")
        sys.exit(NOT_YET_SEALED)

    rows = [_loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()]
    topups = [row for row in rows if row and row.get("event") == "topup"]
    if not topups:
        click.echo("chutes-topup-multisig: NOT_YET_SEALED: no Chutes top-up rows yet")
        sys.exit(NOT_YET_SEALED)
    bad = [
        row.get("seq")
        for row in topups
        if not row.get("tx_hash") or not row.get("spend_authority_reference")
    ]
    if bad:
        click.echo(
            f"chutes-topup-multisig: FAIL: top-up rows missing tx/signature reference: {bad}",
            err=True,
        )
        sys.exit(FAIL)
    click.echo("chutes-topup-multisig: OK (top-up rows carry tx + spend authority references)")
    sys.exit(OK)


def _loads(line: str) -> dict[str, Any] | None:
    try:
        value = json.loads(line)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


__all__ = ["chutes_topup_multisig"]
