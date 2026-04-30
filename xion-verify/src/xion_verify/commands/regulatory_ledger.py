"""`xion-verify regulatory-ledger` — GOVERNANCE_LEDGER state-actor rows."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import click

from xion_verify.exit_codes import FAIL, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root

_LEDGER = "ledgers/GOVERNANCE_LEDGER.jsonl"
_SAFETY_LEDGER = "ledgers/SAFETY_LEDGER.jsonl"
_SCHEMA = "docs/schemas/ledger-governance.yaml"
_ZERO = "0" * 64
_REQUIRED = {
    "schema_version",
    "seq",
    "prev_hash",
    "this_hash",
    "class",
    "state_actor_identifier",
    "jurisdiction",
    "demand_summary_hash",
    "demand_artifact_uri",
    "covenant_principles_touched",
    "invariants_touched",
    "response_category",
    "response_artifact_uri",
    "user_notification",
    "linked_safety_ledger_seq",
    "date",
}


def check_regulatory_ledger(repo_root: Path, ledger_rel: str = _LEDGER, *, check_safety_link: bool = False) -> list[str]:
    if not (repo_root / _SCHEMA).is_file():
        return [f"missing schema: {_SCHEMA}"]
    path = repo_root / ledger_rel
    if not path.is_file():
        return [f"missing ledger: {ledger_rel}"]
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    errors: list[str] = []
    prev = _ZERO
    for expected_seq, row in enumerate(rows):
        missing = _REQUIRED - row.keys()
        if missing:
            errors.append(f"row {expected_seq}: missing fields {sorted(missing)}")
            continue
        if row["seq"] != expected_seq:
            errors.append(f"row {expected_seq}: seq mismatch")
        if row["prev_hash"] != prev:
            errors.append(f"row {expected_seq}: prev_hash mismatch")
        if row["this_hash"] != _hash_row(row):
            errors.append(f"row {expected_seq}: this_hash mismatch")
        if row["class"] in {"B", "C", "D"} and not (
            row["covenant_principles_touched"] or row["invariants_touched"]
        ):
            errors.append(f"row {expected_seq}: class {row['class']} needs covenant or invariant touch")
        if row["class"] == "B" and not row["invariants_touched"]:
            errors.append(f"row {expected_seq}: class B needs invariants_touched")
        if row["class"] == "C" and row["linked_safety_ledger_seq"] is None:
            errors.append(f"row {expected_seq}: class C needs linked_safety_ledger_seq")
        if (
            check_safety_link
            and row["class"] == "C"
            and row["linked_safety_ledger_seq"] is not None
            and not _safety_seq_exists(repo_root, int(row["linked_safety_ledger_seq"]))
        ):
            errors.append(f"row {expected_seq}: linked_safety_ledger_seq {row['linked_safety_ledger_seq']} not found")
        prev = row["this_hash"]
    return errors


def _hash_row(row: dict[str, Any]) -> str:
    body = {key: value for key, value in row.items() if key != "this_hash"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def _safety_seq_exists(repo_root: Path, seq: int) -> bool:
    path = repo_root / _SAFETY_LEDGER
    if not path.is_file():
        return False
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("seq") == seq:
            return True
    return False


@click.command(name="regulatory-ledger", help="Verify GOVERNANCE_LEDGER state-actor-interaction rows.")
@click.option("--check-safety-link", is_flag=True, help="For class C rows, require linked SAFETY_LEDGER seq to exist.")
def regulatory_ledger(check_safety_link: bool) -> None:
    try:
        repo_root = find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"regulatory-ledger: FAIL: {exc}", err=True)
        sys.exit(FAIL)
    errors = check_regulatory_ledger(repo_root, check_safety_link=check_safety_link)
    if errors:
        for error in errors:
            click.echo(f"regulatory-ledger: FAIL: {error}", err=True)
        sys.exit(FAIL)
    rows = sum(1 for line in (repo_root / _LEDGER).read_text(encoding="utf-8").splitlines() if line.strip())
    click.echo(f"regulatory-ledger: OK ({rows} state-actor row(s) verified)")
    sys.exit(OK)


__all__ = ["check_regulatory_ledger", "regulatory_ledger"]
