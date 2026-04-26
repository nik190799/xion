"""`xion-verify substrate-portability` — dry-run ledger verification."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import click

from xion_verify.exit_codes import FAIL, NOT_YET_SEALED, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root

_LEDGER = "ledgers/SUBSTRATE_DRYRUN_LEDGER.jsonl"
_ZERO = "0" * 64
_NON_LAPTOP_SUBSTRATE_PREFIXES = ("akash", "aleph")
_PLACEHOLDER_SECONDARY_IDS = {
    "",
    "secondary-placeholder",
    "operator-laptop-secondary",
    "laptop-secondary",
}


def check_substrate_portability(repo_root: Path, ledger_rel: str = _LEDGER) -> list[str]:
    _code, messages = evaluate_substrate_portability(repo_root, ledger_rel=ledger_rel)
    return messages


def evaluate_substrate_portability(repo_root: Path, ledger_rel: str = _LEDGER) -> tuple[int, list[str]]:
    path = repo_root / ledger_rel
    if not path.is_file():
        return NOT_YET_SEALED, [f"missing dry-run ledger: {ledger_rel}"]
    errors: list[str] = []
    has_non_laptop_secondary = False
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows:
        return NOT_YET_SEALED, ["dry-run ledger has no rows"]
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
        secondary_id = str(row.get("secondary_substrate_id", "")).strip().lower()
        if secondary_id not in _PLACEHOLDER_SECONDARY_IDS and secondary_id.startswith(
            _NON_LAPTOP_SUBSTRATE_PREFIXES
        ):
            has_non_laptop_secondary = True
        prev = row.get("this_hash", "")
    if errors:
        return FAIL, errors
    if not has_non_laptop_secondary:
        return NOT_YET_SEALED, ["no Akash/Aleph non-laptop secondary substrate dry-run row found"]
    return OK, []


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
    code, messages = evaluate_substrate_portability(repo_root)
    if messages:
        label = "NOT_YET_SEALED" if code == NOT_YET_SEALED else "FAIL"
        for message in messages:
            click.echo(f"substrate-portability: {label}: {message}", err=(code == FAIL))
        sys.exit(code)
    click.echo("substrate-portability: OK (dry-run ledger chain and tip parity verified)")
    sys.exit(OK)


__all__ = ["check_substrate_portability", "evaluate_substrate_portability", "substrate_portability"]
