"""Verify model-promotion rows follow audition -> canary -> primary -> retired."""

from __future__ import annotations

import json
import os
import sys
import hashlib
from pathlib import Path

import click

from xion_verify.exit_codes import FAIL, NOT_YET_SEALED, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root

_NEXT = {None: "audition", "audition": "canary", "canary": "primary", "primary": "retired"}
_GENESIS_APPROVER = "operator-genesis-signature"
_GENESIS_PIN_REL = "genesis/PINNED_HASH.txt"


def _genesis_evidence_hash(repo: Path) -> str | None:
    pin = repo / _GENESIS_PIN_REL
    if not pin.is_file():
        return None
    return hashlib.sha256(pin.read_bytes()).hexdigest()


def check_model_promotion_discipline(repo: Path, ledger: Path | None = None) -> tuple[list[str], list[str]]:
    notes: list[str] = []
    errors: list[str] = []
    ledger_path = ledger or Path(os.environ.get(
        "XION_MODEL_REGISTRY_LEDGER",
        str(repo / "ledgers/MODEL_REGISTRY_LEDGER.jsonl"),
    ))
    if not ledger_path.is_absolute():
        ledger_path = repo / ledger_path
    if not ledger_path.is_file():
        notes.append("no promotion ledger yet")
        return errors, notes
    try:
        rows = [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except json.JSONDecodeError as exc:
        return [f"invalid JSONL: {exc}"], notes
    if not rows:
        notes.append("no promotion rows yet")
        return errors, notes

    genesis_hash = _genesis_evidence_hash(repo)
    if genesis_hash is None:
        errors.append(f"missing {_GENESIS_PIN_REL}")
        return errors, notes

    current: dict[str, str | None] = {}
    seen_slug_rows: dict[str, int] = {}
    for idx, row in enumerate(rows):
        slug = str(row.get("model_slug") or "")
        if not slug:
            errors.append(f"row {idx} missing model_slug")
            continue
        event = row.get("event", "promotion")
        seen_count = seen_slug_rows.get(slug, 0)
        expected_from = current.get(slug)
        if event == "genesis_seed":
            if seen_count != 0:
                errors.append(f"row {idx} genesis_seed must be first row for {slug}")
            if row.get("from_state") is not None or row.get("to_state") != "primary":
                errors.append(f"row {idx} invalid genesis_seed transition")
            if row.get("evidence_bundle_hash") != genesis_hash:
                errors.append(f"row {idx} genesis_seed evidence hash mismatch")
            if row.get("approver") != _GENESIS_APPROVER:
                errors.append(f"row {idx} genesis_seed approver mismatch")
            current[slug] = "primary"
        elif event == "promotion":
            if row.get("from_state") != expected_from:
                errors.append(f"row {idx} from_state mismatch")
            if row.get("to_state") != _NEXT.get(expected_from):
                errors.append(f"row {idx} invalid transition")
            current[slug] = row.get("to_state")
        else:
            errors.append(f"row {idx} unknown event {event!r}")
        if not row.get("evidence_bundle_hash") or not row.get("approver"):
            errors.append(f"row {idx} missing evidence/approver")
        seen_slug_rows[slug] = seen_count + 1
    return errors, notes


@click.command(name="model-promotion-discipline")
@click.option("--ledger", "ledger_path", type=click.Path(path_type=Path), default=None)
def model_promotion_discipline(ledger_path: Path | None) -> None:
    try:
        repo = find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"model-promotion-discipline: FAIL: {exc}", err=True)
        sys.exit(FAIL)
    errors, notes = check_model_promotion_discipline(repo, ledger_path)
    if notes and not errors:
        click.echo(f"model-promotion-discipline: NOT_YET_SEALED: {notes[0]}")
        sys.exit(NOT_YET_SEALED)
    if errors:
        for error in errors:
            click.echo(f"model-promotion-discipline: FAIL: {error}", err=True)
        sys.exit(FAIL)
    click.echo("model-promotion-discipline: OK (promotion chain disciplined)")
    sys.exit(OK)


__all__ = ["check_model_promotion_discipline", "model_promotion_discipline"]
