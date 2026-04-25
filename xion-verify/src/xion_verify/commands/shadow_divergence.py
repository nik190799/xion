"""Verify SHADOW_LEDGER rows are structurally bounded."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import click

from xion_verify.exit_codes import FAIL, NOT_YET_SEALED, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root


@click.command(name="shadow-divergence")
@click.option("--ledger", "ledger_path", type=click.Path(path_type=Path), default=None)
def shadow_divergence(ledger_path: Path | None) -> None:
    try:
        repo = find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"shadow-divergence: FAIL: {exc}", err=True)
        sys.exit(FAIL)
    ledger = ledger_path or Path(os.environ.get("XION_SHADOW_LEDGER", str(repo / "ledgers/SHADOW_LEDGER.jsonl")))
    if not ledger.is_absolute():
        ledger = repo / ledger
    if not ledger.is_file():
        click.echo("shadow-divergence: NOT_YET_SEALED: no SHADOW_LEDGER rows yet")
        sys.exit(NOT_YET_SEALED)
    scores = []
    for line in ledger.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        scores.append(float(row.get("divergence_score", 1.0)))
    if not scores:
        click.echo("shadow-divergence: NOT_YET_SEALED: no SHADOW_LEDGER rows yet")
        sys.exit(NOT_YET_SEALED)
    p95 = sorted(scores)[int(0.95 * (len(scores) - 1))]
    threshold = float(os.environ.get("XION_SHADOW_DIVERGENCE_P95_MAX", "0.85"))
    if p95 > threshold:
        click.echo(f"shadow-divergence: FAIL: p95={p95:.3f} > {threshold:.3f}", err=True)
        sys.exit(FAIL)
    click.echo(f"shadow-divergence: OK (p95={p95:.3f})")
    sys.exit(OK)


__all__ = ["shadow_divergence"]
