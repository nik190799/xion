"""`xion-verify mcp-export` — read-only constitutional facts bundle for agents."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import click

from xion_verify.exit_codes import FAIL, OK
from xion_verify.hashing import sha256_file
from xion_verify.leveling import load_level_schemas
from xion_verify.repo import RepoRootNotFound, find_repo_root

_KW_HEADING = re.compile(r"^### (?P<id>KW-[A-Z0-9-]+) — (?P<title>.+)$")


def _hash_if_present(repo_root: Path, rel: str) -> str | None:
    path = repo_root / rel
    return sha256_file(path) if path.is_file() else None


def _known_weaknesses(repo_root: Path) -> list[dict[str, str]]:
    path = repo_root / "KNOWN_WEAKNESSES.md"
    if not path.is_file():
        return []
    out: list[dict[str, str]] = []
    in_open = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## Open"):
            in_open = True
            continue
        if in_open and line.startswith("## ") and not line.startswith("## Open"):
            break
        if not in_open:
            continue
        match = _KW_HEADING.match(line)
        if match:
            out.append({"id": match.group("id"), "title": match.group("title")})
    return out


def _proposal_ledger_status(repo_root: Path) -> dict[str, Any]:
    ledger = repo_root / "PROPOSAL_LEDGER.jsonl"
    if not ledger.is_file():
        ledger = repo_root / "ledgers" / "PROPOSAL_LEDGER.jsonl"
    if not ledger.is_file():
        return {"present": False, "rows": 0}
    rows = sum(1 for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip())
    return {"present": True, "path": ledger.relative_to(repo_root).as_posix(), "rows": rows}


@click.command(name="mcp-export", help="Emit a read-only JSON facts bundle for agent/MCP wrappers.")
@click.option("--pretty/--compact", default=True, help="Pretty-print JSON output.")
def mcp_export(pretty: bool) -> None:
    try:
        repo_root = find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"mcp-export: FAIL: {exc}", err=True)
        sys.exit(FAIL)

    schemas = load_level_schemas(repo_root)
    payload: dict[str, Any] = {
        "schema_version": 1,
        "mode": "read_only",
        "property": "Expose constitutional and contribution-planning facts to coding agents without write authority.",
        "guardrails": [
            "no_state_writes",
            "no_proposal_submission",
            "no_key_custody",
            "no_agent_governance_actor",
        ],
        "hashes": {
            "covenant": _hash_if_present(repo_root, "genesis/COVENANT.md"),
            "invariants": _hash_if_present(repo_root, "genesis/INVARIANTS.md"),
            "levels": _hash_if_present(repo_root, "docs/schemas/levels.yaml"),
            "roles": _hash_if_present(repo_root, "docs/schemas/roles.yaml"),
        },
        "levels": schemas.levels.get("levels", []) if schemas else [],
        "roles": {
            "actors": schemas.roles.get("actors", []) if schemas else [],
            "github_identity_map": schemas.roles.get("github_identity_map", {}) if schemas else {},
        },
        "known_weaknesses_open": _known_weaknesses(repo_root),
        "proposal_ledger": _proposal_ledger_status(repo_root),
    }
    click.echo(json.dumps(payload, indent=2 if pretty else None, sort_keys=True))
    sys.exit(OK)
