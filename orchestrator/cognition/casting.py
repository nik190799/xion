"""Casting Pipeline: deterministic Agent Soul -> runtime faculty records."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_AGENT_SOULS_REL = Path("genesis/AGENT_SOULS")
_ALLOWLIST_REL = Path("genesis/HERMES_TOOL_ALLOWLIST.yaml")
_CAST_LEDGER_REL = Path("ledgers/AGENT_CAST_LEDGER.jsonl")
_PARENT_SOUL_REL = Path("genesis/SOUL.md")


@dataclass(frozen=True)
class CastResult:
    agent_id: str
    agent_soul_hash: str
    parent_soul_hash: str
    hermes_pin: str
    smoke_test_pass: bool


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_yaml(path: Path) -> dict[str, Any]:
    # PyYAML is intentionally owned by xion-verify. The core orchestrator
    # package remains importable with zero dependencies; only the operator
    # casting command needs YAML parsing.
    import yaml

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: top-level YAML value must be a mapping")
    return data


def _repo_root(start: Path | None = None) -> Path:
    here = (start or Path.cwd()).resolve()
    for candidate in (here, *here.parents):
        if (candidate / "genesis" / "GENESIS_ARTIFACT.md").is_file() and (
            candidate / "docs" / "00-INDEX.md"
        ).is_file():
            return candidate
    raise RuntimeError(f"No Xion repo root at or above {here}")


def _append_row(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")


def _validate_soul(repo_root: Path, soul_path: Path, allowlist: dict[str, Any]) -> CastResult:
    soul = _load_yaml(soul_path)
    agent_id = soul.get("agent_id")
    if not isinstance(agent_id, str) or not agent_id:
        raise ValueError(f"{soul_path}: agent_id must be a non-empty string")
    if agent_id == "arbiter":
        raise ValueError("the Arbiter is not an Agent Soul and must not be cast")

    parent_hash = _sha256_file(repo_root / _PARENT_SOUL_REL)
    if soul.get("extends_soul_hash") != parent_hash:
        raise ValueError(f"{soul_path}: extends_soul_hash does not match {_PARENT_SOUL_REL.as_posix()}")

    agent_allowlist = allowlist.get("agent_tool_allowlist", {})
    if not isinstance(agent_allowlist, dict):
        raise ValueError(f"{_ALLOWLIST_REL.as_posix()}: agent_tool_allowlist must be a mapping")
    entry = agent_allowlist.get(agent_id)
    if not isinstance(entry, dict):
        raise ValueError(f"{soul_path}: no allowlist entry for {agent_id}")

    soul_tools = set(soul.get("allowed_tools", []))
    allowed_tools = set(entry.get("allowed_tools", []))
    extra = sorted(soul_tools - allowed_tools)
    if extra:
        raise ValueError(f"{soul_path}: tools not in allowlist for {agent_id}: {', '.join(extra)}")

    outputs = soul.get("output_destinations")
    if not isinstance(outputs, list) or not outputs:
        raise ValueError(f"{soul_path}: output_destinations must be a non-empty list")

    hermes_pin = allowlist.get("hermes_pin", {}).get("commit")
    if not isinstance(hermes_pin, str) or not hermes_pin:
        raise ValueError(f"{_ALLOWLIST_REL.as_posix()}: hermes_pin.commit must be present")

    return CastResult(
        agent_id=agent_id,
        agent_soul_hash=_sha256_file(soul_path),
        parent_soul_hash=parent_hash,
        hermes_pin=hermes_pin,
        smoke_test_pass=True,
    )


def cast_pool(start: Path | None = None) -> list[CastResult]:
    """Smoke-test all Agent Souls and append cast rows to AGENT_CAST_LEDGER."""

    repo_root = _repo_root(start)
    allowlist = _load_yaml(repo_root / _ALLOWLIST_REL)
    souls_dir = repo_root / _AGENT_SOULS_REL
    soul_paths = sorted(p for p in souls_dir.glob("*.yaml") if p.is_file())
    if not soul_paths:
        raise RuntimeError(f"No Agent Soul YAML files found in {_AGENT_SOULS_REL.as_posix()}")

    cast_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    ledger = repo_root / _CAST_LEDGER_REL
    results: list[CastResult] = []
    for soul_path in soul_paths:
        try:
            result = _validate_soul(repo_root, soul_path, allowlist)
        except Exception as exc:
            _append_row(
                ledger,
                {
                    "schema_version": 1,
                    "event": "cast_failed",
                    "agent_id": soul_path.stem,
                    "agent_soul_hash": _sha256_file(soul_path),
                    "parent_soul_hash": _sha256_file(repo_root / _PARENT_SOUL_REL),
                    "hermes_pin": allowlist.get("hermes_pin", {}).get("commit", "UNKNOWN"),
                    "cast_at": cast_at,
                    "smoke_test_pass": False,
                    "reason": str(exc),
                },
            )
            raise
        _append_row(
            ledger,
            {
                "schema_version": 1,
                "event": "cast_succeeded",
                "agent_id": result.agent_id,
                "agent_soul_hash": result.agent_soul_hash,
                "parent_soul_hash": result.parent_soul_hash,
                "hermes_pin": result.hermes_pin,
                "cast_at": cast_at,
                "smoke_test_pass": result.smoke_test_pass,
            },
        )
        results.append(result)

    return results
