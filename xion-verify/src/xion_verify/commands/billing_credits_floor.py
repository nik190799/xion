"""Verify BILLING_LEDGER freshness and Chutes credit floor."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import click

from xion_verify.exit_codes import FAIL, NOT_YET_SEALED, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root


@click.command(name="billing-credits-floor")
@click.option("--ledger", "ledger_path", type=click.Path(path_type=Path), default=None)
def billing_credits_floor(ledger_path: Path | None) -> None:
    try:
        repo = find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"billing-credits-floor: FAIL: {exc}", err=True)
        sys.exit(FAIL)

    ledger = ledger_path or Path(os.environ.get(
        "XION_CHUTES_BILLING_LEDGER",
        str(repo / "ledgers/BILLING_LEDGER.jsonl"),
    ))
    if not ledger.is_absolute():
        ledger = repo / ledger
    if not ledger.is_file():
        click.echo(
            "billing-credits-floor: NOT_YET_SEALED: BILLING_LEDGER has no rows yet",
        )
        sys.exit(NOT_YET_SEALED)

    rows = [_loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows = [row for row in rows if row is not None]
    if not rows:
        click.echo("billing-credits-floor: NOT_YET_SEALED: BILLING_LEDGER is empty")
        sys.exit(NOT_YET_SEALED)
    latest = rows[-1]
    max_stale_s = int(os.environ.get("XION_CHUTES_BILLING_MAX_STALENESS_S", "900"))
    age_s = (time.time_ns() - int(latest["timestamp_utc_ns"])) / 1_000_000_000
    if age_s > max_stale_s:
        click.echo(
            f"billing-credits-floor: FAIL: latest row is stale ({age_s:.1f}s > {max_stale_s}s)",
            err=True,
        )
        sys.exit(FAIL)
    floor = float(os.environ.get("XION_CHUTES_CREDIT_FLOOR_USD", "5.00"))
    balance = latest.get("balance_usd")
    if balance is not None and float(balance) < floor:
        click.echo(
            f"billing-credits-floor: FAIL: balance_usd={float(balance):.2f} below floor={floor:.2f}",
            err=True,
        )
        sys.exit(FAIL)
    click.echo("billing-credits-floor: OK (fresh Chutes billing row above configured floor)")
    sys.exit(OK)


def _loads(line: str) -> dict[str, Any] | None:
    try:
        value = json.loads(line)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


__all__ = ["billing_credits_floor"]
