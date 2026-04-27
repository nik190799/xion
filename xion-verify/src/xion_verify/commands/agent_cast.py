"""`xion-verify agent-cast` — Agent cast ledger verifier."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import click

from xion_verify.commands.agent_souls import agent_soul_hashes, check_agent_souls, load_agent_soul
from xion_verify.commands.hermes_runtime import check_hermes_runtime, load_allowlist
from xion_verify.exit_codes import FAIL, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root

_CAST_LEDGER_REL = "ledgers/AGENT_CAST_LEDGER.jsonl"
_REQUIRED_FIELDS = (
    "schema_version",
    "event",
    "agent_id",
    "agent_soul_hash",
    "parent_soul_hash",
    "hermes_pin",
    "cast_at",
    "smoke_test_pass",
)
_ALLOWED_EVENTS = {"cast_succeeded", "cast_failed"}


def _iter_cast_rows(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"{_CAST_LEDGER_REL}:{lineno}: invalid JSON: {exc}")
            continue
        if not isinstance(row, dict):
            errors.append(f"{_CAST_LEDGER_REL}:{lineno}: row must be a JSON object")
            continue
        rows.append(row)
    return rows, errors


def check_agent_cast(repo_root: Path) -> tuple[list[str], list[str], int]:
    errors: list[str] = []
    notes: list[str] = []

    runtime_errors, runtime_notes = check_hermes_runtime(repo_root)
    errors.extend(runtime_errors)
    notes.extend(runtime_notes)

    soul_errors, _ = check_agent_souls(repo_root)
    errors.extend(soul_errors)

    ledger_path = repo_root / _CAST_LEDGER_REL
    if not ledger_path.is_file():
        errors.append(f"missing {_CAST_LEDGER_REL}")
        return errors, notes, 0

    rows, row_errors = _iter_cast_rows(ledger_path)
    errors.extend(row_errors)
    if errors:
        return errors, notes, len(rows)

    if not rows:
        notes.append("no live cast rows yet; ledger is seeded and ready for xion cast pool")
        return errors, notes, 0

    soul_hashes = agent_soul_hashes(repo_root)
    allowlist = load_allowlist(repo_root)
    hermes_commit = allowlist.get("hermes_pin", {}).get("commit")

    latest_by_agent: dict[str, tuple[int, dict[str, object]]] = {}

    for idx, row in enumerate(rows, start=1):
        missing = [field for field in _REQUIRED_FIELDS if field not in row]
        if missing:
            errors.append(f"{_CAST_LEDGER_REL}:{idx}: missing required fields: {', '.join(missing)}")
            continue
        event = row.get("event")
        if event not in _ALLOWED_EVENTS:
            errors.append(f"{_CAST_LEDGER_REL}:{idx}: unknown event {event!r}")
        if event == "cast_failed" and not row.get("reason"):
            errors.append(f"{_CAST_LEDGER_REL}:{idx}: cast_failed rows must include reason")
        if row.get("agent_id") == "arbiter":
            errors.append(f"{_CAST_LEDGER_REL}:{idx}: arbiter must not be cast")

        agent_id = row.get("agent_id")
        if isinstance(agent_id, str) and event == "cast_succeeded":
            latest_by_agent[agent_id] = (idx, row)
        if event == "cast_failed" and row.get("smoke_test_pass") is True:
            errors.append(f"{_CAST_LEDGER_REL}:{idx}: cast_failed rows must not have smoke_test_pass=true")

    for idx, row in latest_by_agent.values():
        agent_id = row.get("agent_id")
        expected_soul_hash = soul_hashes.get(agent_id)
        if expected_soul_hash is None:
            errors.append(f"{_CAST_LEDGER_REL}:{idx}: no Agent Soul for {agent_id!r}")
            continue
        if row.get("agent_soul_hash") != expected_soul_hash:
            errors.append(
                f"{_CAST_LEDGER_REL}:{idx}: agent_soul_hash mismatch for {agent_id} "
                f"(expected {expected_soul_hash})"
            )

        soul_path = repo_root / "genesis" / "AGENT_SOULS" / f"{agent_id}.yaml"
        soul = load_agent_soul(soul_path)
        if row.get("parent_soul_hash") != soul.get("extends_soul_hash"):
            errors.append(f"{_CAST_LEDGER_REL}:{idx}: parent_soul_hash mismatch for {agent_id}")
        if row.get("hermes_pin") != hermes_commit:
            errors.append(f"{_CAST_LEDGER_REL}:{idx}: hermes_pin mismatch for {agent_id}")
        if event == "cast_succeeded" and row.get("smoke_test_pass") is not True:
            errors.append(f"{_CAST_LEDGER_REL}:{idx}: cast_succeeded requires smoke_test_pass=true")

    return errors, notes, len(rows)


@click.command(name="agent-cast")
def agent_cast() -> None:
    """Verify the Agent cast ledger against Agent Souls and the Hermes pin."""

    try:
        repo_root = find_repo_root(Path.cwd())
    except RepoRootNotFound as exc:
        click.echo(f"agent-cast: FAIL: {exc}", err=True)
        raise SystemExit(FAIL) from None

    errors, notes, count = check_agent_cast(repo_root)
    if errors:
        for error in errors:
            click.echo(f"agent-cast: FAIL: {error}", err=True)
        raise SystemExit(FAIL)

    click.echo(f"agent-cast: OK ({count} cast row(s) verified)")
    for note in notes:
        click.echo(f"agent-cast: {note}")
    raise SystemExit(OK)
