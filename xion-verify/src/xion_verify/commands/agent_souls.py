"""`xion-verify agent-souls` — content-addressed Agent Soul verifier."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import click
import yaml

from xion_verify.commands.hermes_runtime import load_allowlist
from xion_verify.exit_codes import FAIL, OK
from xion_verify.hashing import sha256_file
from xion_verify.repo import RepoRootNotFound, find_repo_root

_AGENT_SOULS_REL = "genesis/AGENT_SOULS"
_PARENT_SOUL_REL = "genesis/SOUL.md"
_MANIFEST_REL = "genesis/AGENT_SOULS/MANIFEST.txt"
_REQUIRED_FIELDS = (
    "schema_version",
    "agent_id",
    "soul_version",
    "extends_soul_hash",
    "purpose",
    "trigger",
    "allowed_tools",
    "forbidden_tools",
    "mcp_servers_allowed",
    "cost_envelope",
    "output_destinations",
    "arbiter_class",
    "limits",
    "deprecation_path",
)


def agent_soul_paths(repo_root: Path) -> list[Path]:
    souls_dir = repo_root / _AGENT_SOULS_REL
    return sorted(p for p in souls_dir.glob("*.yaml") if p.is_file())


def load_agent_soul(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path.name}: top-level YAML value must be a mapping")
    return data


def agent_soul_hashes(repo_root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for path in agent_soul_paths(repo_root):
        data = load_agent_soul(path)
        agent_id = data.get("agent_id")
        if isinstance(agent_id, str):
            out[agent_id] = sha256_file(path)
    return out


def _manifest_payload_hash(repo_root: Path) -> str:
    souls_dir = repo_root / _AGENT_SOULS_REL
    files = sorted(
        p
        for p in souls_dir.iterdir()
        if p.is_file() and p.name != "MANIFEST.txt"
    )
    h = hashlib.sha256()
    for path in files:
        h.update(path.read_bytes())
    return h.hexdigest()


def _manifest_declared_hash(repo_root: Path) -> str | None:
    manifest = repo_root / _MANIFEST_REL
    if not manifest.is_file():
        return None
    for raw in manifest.read_text(encoding="utf-8").splitlines():
        if raw.startswith("manifest_payload_sha256:"):
            return raw.split(":", 1)[1].strip()
    return None


def _manifest_file_hashes(repo_root: Path) -> dict[str, str]:
    manifest = repo_root / _MANIFEST_REL
    out: dict[str, str] = {}
    if not manifest.is_file():
        return out
    for raw in manifest.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or " sha256:" not in line:
            continue
        rel, digest = line.split(" sha256:", 1)
        out[rel.strip()] = digest.strip()
    return out


def check_agent_souls(repo_root: Path) -> tuple[list[str], int]:
    errors: list[str] = []
    souls_dir = repo_root / _AGENT_SOULS_REL
    if not souls_dir.is_dir():
        return [f"missing {_AGENT_SOULS_REL}/"], 0

    schema_path = souls_dir / "_SCHEMA.md"
    if not schema_path.is_file():
        errors.append(f"missing {_AGENT_SOULS_REL}/_SCHEMA.md")

    manifest_declared = _manifest_declared_hash(repo_root)
    if manifest_declared is None:
        errors.append(f"missing {_MANIFEST_REL} or manifest_payload_sha256")
    else:
        actual = _manifest_payload_hash(repo_root)
        if manifest_declared != actual:
            errors.append(
                f"{_MANIFEST_REL}: manifest_payload_sha256 mismatch "
                f"(declared={manifest_declared}, actual={actual})"
            )

    manifest_hashes = _manifest_file_hashes(repo_root)
    expected_paths = sorted(
        p.relative_to(repo_root).as_posix()
        for p in souls_dir.iterdir()
        if p.is_file() and p.name != "MANIFEST.txt"
    )
    missing_manifest_paths = [rel for rel in expected_paths if rel not in manifest_hashes]
    extra_manifest_paths = sorted(set(manifest_hashes) - set(expected_paths))
    if missing_manifest_paths:
        errors.append(
            f"{_MANIFEST_REL}: missing per-file sha256 entries: {', '.join(missing_manifest_paths)}"
        )
    if extra_manifest_paths:
        errors.append(
            f"{_MANIFEST_REL}: unknown per-file sha256 entries: {', '.join(extra_manifest_paths)}"
        )
    for rel in expected_paths:
        declared = manifest_hashes.get(rel)
        if declared is None:
            continue
        actual = sha256_file(repo_root / rel)
        if declared != actual:
            errors.append(
                f"{_MANIFEST_REL}: sha256 mismatch for {rel} "
                f"(declared={declared}, actual={actual})"
            )

    parent_hash = sha256_file(repo_root / _PARENT_SOUL_REL)
    try:
        allowlist = load_allowlist(repo_root)
    except Exception as exc:  # pragma: no cover - exact failure is covered by hermes-runtime
        errors.append(f"cannot load genesis/HERMES_TOOL_ALLOWLIST.yaml: {exc}")
        allowlist = {}

    agent_allowlist = allowlist.get("agent_tool_allowlist", {})
    if not isinstance(agent_allowlist, dict):
        errors.append("genesis/HERMES_TOOL_ALLOWLIST.yaml: agent_tool_allowlist must be a mapping")
        agent_allowlist = {}

    paths = agent_soul_paths(repo_root)
    for path in paths:
        try:
            data = load_agent_soul(path)
        except (OSError, UnicodeDecodeError, yaml.YAMLError, ValueError) as exc:
            errors.append(f"{path.relative_to(repo_root).as_posix()}: invalid Agent Soul: {exc}")
            continue

        rel = path.relative_to(repo_root).as_posix()
        missing = [field for field in _REQUIRED_FIELDS if field not in data]
        if missing:
            errors.append(f"{rel}: missing required fields: {', '.join(missing)}")

        agent_id = data.get("agent_id")
        if agent_id == "arbiter":
            errors.append(f"{rel}: arbiter must not be an Agent Soul")
        if not isinstance(agent_id, str) or not agent_id:
            errors.append(f"{rel}: agent_id must be a non-empty string")
            continue

        if data.get("extends_soul_hash") != parent_hash:
            errors.append(
                f"{rel}: extends_soul_hash mismatch "
                f"(expected current {_PARENT_SOUL_REL} hash {parent_hash})"
            )

        allowed_tools = data.get("allowed_tools")
        if not isinstance(allowed_tools, list) or not all(isinstance(t, str) for t in allowed_tools):
            errors.append(f"{rel}: allowed_tools must be a list of strings")
            allowed_tools = []

        allowlist_entry = agent_allowlist.get(agent_id)
        if not isinstance(allowlist_entry, dict):
            errors.append(f"{rel}: no allowlist entry for {agent_id}")
            allowlist_tools: set[str] = set()
        else:
            raw_tools = allowlist_entry.get("allowed_tools", [])
            allowlist_tools = set(raw_tools) if isinstance(raw_tools, list) else set()

        extra = sorted(set(allowed_tools) - allowlist_tools)
        if extra:
            errors.append(f"{rel}: allowed_tools not in allowlist for {agent_id}: {', '.join(extra)}")

    return errors, len(paths)


@click.command(name="agent-souls")
def agent_souls() -> None:
    """Verify Agent Souls parse, extend SOUL.md, and reference only allowlisted tools."""

    try:
        repo_root = find_repo_root(Path.cwd())
    except RepoRootNotFound as exc:
        click.echo(f"agent-souls: FAIL: {exc}", err=True)
        raise SystemExit(FAIL) from None

    errors, count = check_agent_souls(repo_root)
    if errors:
        for error in errors:
            click.echo(f"agent-souls: FAIL: {error}", err=True)
        raise SystemExit(FAIL)

    click.echo(f"agent-souls: OK ({count} Agent Soul file(s) verified)")
    raise SystemExit(OK)
