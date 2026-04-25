"""Verify model-promotion rows follow audition -> canary -> primary -> retired."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import click

from xion_verify.exit_codes import FAIL, NOT_YET_SEALED, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root

_NEXT = {None: "audition", "audition": "canary", "canary": "primary", "primary": "retired"}


@click.command(name="model-promotion-discipline")
@click.option("--ledger", "ledger_path", type=click.Path(path_type=Path), default=None)
def model_promotion_discipline(ledger_path: Path | None) -> None:
    try:
        repo = find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"model-promotion-discipline: FAIL: {exc}", err=True)
        sys.exit(FAIL)
    ledger = ledger_path or Path(os.environ.get(
        "XION_MODEL_REGISTRY_LEDGER",
        str(repo / "ledgers/MODEL_REGISTRY_LEDGER.jsonl"),
    ))
    if not ledger.is_absolute():
        ledger = repo / ledger
    if not ledger.is_file():
        click.echo("model-promotion-discipline: NOT_YET_SEALED: no promotion ledger yet")
        sys.exit(NOT_YET_SEALED)
    rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows:
        click.echo("model-promotion-discipline: NOT_YET_SEALED: no promotion rows yet")
        sys.exit(NOT_YET_SEALED)
    current: dict[str, str | None] = {}
    for idx, row in enumerate(rows):
        slug = str(row.get("model_slug") or "")
        expected_from = current.get(slug)
        if row.get("from_state") != expected_from:
            click.echo(f"model-promotion-discipline: FAIL: row {idx} from_state mismatch", err=True)
            sys.exit(FAIL)
        if row.get("to_state") != _NEXT.get(expected_from):
            click.echo(f"model-promotion-discipline: FAIL: row {idx} invalid transition", err=True)
            sys.exit(FAIL)
        if not row.get("evidence_bundle_hash") or not row.get("approver"):
            click.echo(f"model-promotion-discipline: FAIL: row {idx} missing evidence/approver", err=True)
            sys.exit(FAIL)
        current[slug] = row.get("to_state")
    click.echo("model-promotion-discipline: OK (promotion chain disciplined)")
    sys.exit(OK)


__all__ = ["model_promotion_discipline"]
