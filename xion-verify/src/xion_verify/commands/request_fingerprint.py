"""Verify REQUEST_LEDGER provider-attempt fingerprint fields."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import click

from xion_verify.exit_codes import FAIL, NOT_YET_SEALED, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root


@click.command(name="request-fingerprint")
@click.option("--ledger", "ledger_path", type=click.Path(path_type=Path), default=None)
def request_fingerprint(ledger_path: Path | None) -> None:
    try:
        repo = find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"request-fingerprint: FAIL: {exc}", err=True)
        sys.exit(FAIL)
    ledger = ledger_path or Path(os.environ.get("XION_REQUEST_LEDGER", str(repo / "REQUEST_LEDGER.jsonl")))
    if not ledger.is_absolute():
        ledger = repo / ledger
    if not ledger.is_file():
        click.echo("request-fingerprint: NOT_YET_SEALED: no REQUEST_LEDGER yet")
        sys.exit(NOT_YET_SEALED)
    success_rows = []
    for line in ledger.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("schema_version") == 2 and row.get("outcome") == "success":
            success_rows.append(row)
    if not success_rows:
        click.echo("request-fingerprint: NOT_YET_SEALED: no successful provider-attempt rows yet")
        sys.exit(NOT_YET_SEALED)
    missing = []
    for row in success_rows:
        for field in ("provider_fingerprint", "model_version", "reasoning_tokens", "tee_attestation"):
            if field not in row:
                missing.append((row.get("seq"), field))
    if missing:
        click.echo(f"request-fingerprint: FAIL: missing fields {missing}", err=True)
        sys.exit(FAIL)
    tee_required = os.environ.get("XION_CHUTES_TEE_REQUIRED", "true").strip().lower() in {"1", "true", "yes"}
    if tee_required:
        bad = [
            row.get("seq")
            for row in success_rows
            if row.get("provider_id") == "chutes" and not row.get("tee_attestation")
        ]
        if bad:
            click.echo(f"request-fingerprint: FAIL: Chutes rows missing TEE attestation {bad}", err=True)
            sys.exit(FAIL)
    click.echo("request-fingerprint: OK (provider fingerprint metadata present)")
    sys.exit(OK)


__all__ = ["request_fingerprint"]
