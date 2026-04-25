"""`xion-verify substrate-portability` — dry-run ledger verification."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import click

from xion_verify.exit_codes import FAIL, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root

_LEDGER = "ledgers/SUBSTRATE_DRYRUN_LEDGER.jsonl"
_ZERO = "0" * 64


def check_substrate_portability(repo_root: Path, ledger_rel: str = _LEDGER) -> list[str]:
    path = repo_root / ledger_rel
    if not path.is_file():
        return [f"missing dry-run ledger: {ledger_rel}"]
    errors: list[str] = []
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows:
        return ["dry-run ledger has no rows"]
    prev = _ZERO
    for expected_seq, row in enumerate(rows):
        if row.get("seq") != expected_seq:
            errors.append(f"row {expected_seq}: seq mismatch")
        if row.get("prev_hash") != prev:
            errors.append(f"row {expected_seq}: prev_hash mismatch")
        if row.get("this_hash") != _hash_row(row):
            errors.append(f"row {expected_seq}: this_hash mismatch")
        if row.get("tip_parity") is not True:
            errors.append(f"row {expected_seq}: tip_parity must be true")
        if int(row.get("replayed_rows", 0)) < 1:
            errors.append(f"row {expected_seq}: replayed_rows must be positive")
        prev = row.get("this_hash", "")
    return errors


def _hash_row(row: dict[str, Any]) -> str:
    body = {key: value for key, value in row.items() if key != "this_hash"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


@click.command(name="substrate-portability", help="Verify substrate-portability dry-run ledger.")
def substrate_portability() -> None:
    try:
        repo_root = find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"substrate-portability: FAIL: {exc}", err=True)
        sys.exit(FAIL)
    errors = check_substrate_portability(repo_root)
    if errors:
        for error in errors:
            click.echo(f"substrate-portability: FAIL: {error}", err=True)
        sys.exit(FAIL)
    click.echo("substrate-portability: OK (dry-run ledger chain and tip parity verified)")
    sys.exit(OK)


__all__ = ["check_substrate_portability", "substrate_portability"]
