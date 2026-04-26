"""`xion-verify amendments` — Constitutional Amendment Ledger reader."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import click

from xion_verify.exit_codes import FAIL, NOT_YET_SEALED, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root

_LEDGER = "ledgers/AMENDMENT_LEDGER.jsonl"
_REQUIRED_FIELDS = {
    "as_of_utc_ns",
    "event_type",
    "proposal_path",
    "proposal_sha256",
    "target_artifact",
    "pre_hash",
    "post_hash",
    "status",
}


def read_amendment_rows(repo_root: Path, ledger_rel: str = _LEDGER) -> tuple[int, list[dict[str, Any]] | str]:
    path = repo_root / ledger_rel
    if not path.is_file():
        return NOT_YET_SEALED, f"{ledger_rel} not found"
    rows: list[dict[str, Any]] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError as exc:
            return FAIL, f"{ledger_rel}:{line_no}: invalid JSON: {exc}"
        if not isinstance(row, dict):
            return FAIL, f"{ledger_rel}:{line_no}: row must be object"
        missing = sorted(_REQUIRED_FIELDS - row.keys())
        if missing:
            return FAIL, f"{ledger_rel}:{line_no}: missing fields {missing}"
        if row["status"] not in {"ratification_pending", "ratified", "rejected", "withdrawn"}:
            return FAIL, f"{ledger_rel}:{line_no}: invalid status {row['status']!r}"
        for key in ("proposal_sha256", "pre_hash", "post_hash"):
            value = row.get(key)
            if not isinstance(value, str) or len(value) != 64:
                return FAIL, f"{ledger_rel}:{line_no}: {key} must be 64-char sha256 hex"
        rows.append(row)
    if not rows:
        return NOT_YET_SEALED, f"{ledger_rel} contains no rows"
    return OK, rows


@click.command(name="amendments", help="Read and verify the Constitutional Amendment Ledger.")
def amendments() -> None:
    try:
        repo_root = find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"amendments: FAIL: {exc}", err=True)
        sys.exit(FAIL)

    code, result = read_amendment_rows(repo_root)
    if code == OK:
        rows = result  # type: ignore[assignment]
        pending = sum(1 for row in rows if row.get("status") == "ratification_pending")
        ratified = sum(1 for row in rows if row.get("status") == "ratified")
        click.echo(
            f"amendments: OK (rows={len(rows)} pending={pending} ratified={ratified})"
        )
    elif code == NOT_YET_SEALED:
        click.echo(f"amendments: NOT_YET_SEALED — {result}")
    else:
        click.echo(f"amendments: FAIL: {result}", err=True)
    sys.exit(code)


__all__ = ["amendments", "read_amendment_rows"]
