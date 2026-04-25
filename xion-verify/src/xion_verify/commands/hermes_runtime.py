"""`xion-verify hermes-runtime` — Hermes pin and allowlist verifier."""

from __future__ import annotations

import re
from pathlib import Path

import click
import yaml

from xion_verify.exit_codes import FAIL, OK
from xion_verify.hashing import sha256_file
from xion_verify.repo import RepoRootNotFound, find_repo_root

_ALLOWLIST_REL = "genesis/HERMES_TOOL_ALLOWLIST.yaml"
_ARTIFACT_REL = "genesis/GENESIS_ARTIFACT.md"
_REQUIRED_DISABLED_FLAGS = (
    "skill_self_improvement",
    "autonomous_skill_creation",
    "mcp_server_auto_discovery",
    "user_model_export",
)


def _extract_artifact_value(text: str, key: str) -> str | None:
    match = re.search(rf"^{re.escape(key)}:\s*(?P<value>\S+)\s*$", text, re.MULTILINE)
    return match.group("value") if match else None


def load_allowlist(repo_root: Path) -> dict:
    path = repo_root / _ALLOWLIST_REL
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{_ALLOWLIST_REL} top-level YAML value must be a mapping")
    return data


def check_hermes_runtime(repo_root: Path) -> tuple[list[str], list[str]]:
    """Return (errors, notes) for the Hermes runtime contract."""

    errors: list[str] = []
    notes: list[str] = []

    allowlist_path = repo_root / _ALLOWLIST_REL
    artifact_path = repo_root / _ARTIFACT_REL
    if not allowlist_path.is_file():
        errors.append(f"missing {_ALLOWLIST_REL}")
        return errors, notes
    if not artifact_path.is_file():
        errors.append(f"missing {_ARTIFACT_REL}")
        return errors, notes

    try:
        allowlist = load_allowlist(repo_root)
    except (OSError, UnicodeDecodeError, yaml.YAMLError, ValueError) as exc:
        errors.append(f"{_ALLOWLIST_REL} invalid: {exc}")
        return errors, notes

    if allowlist.get("default_deny") is not True:
        errors.append(f"{_ALLOWLIST_REL}: default_deny must be true")

    flags = allowlist.get("disabled_runtime_flags")
    if not isinstance(flags, dict):
        errors.append(f"{_ALLOWLIST_REL}: disabled_runtime_flags must be a mapping")
    else:
        for name in _REQUIRED_DISABLED_FLAGS:
            if flags.get(name) is not False:
                errors.append(f"{_ALLOWLIST_REL}: disabled_runtime_flags.{name} must be false")

    hermes_pin = allowlist.get("hermes_pin")
    if not isinstance(hermes_pin, dict):
        errors.append(f"{_ALLOWLIST_REL}: hermes_pin must be a mapping")
        hermes_pin = {}

    artifact = artifact_path.read_text(encoding="utf-8")
    artifact_commit = _extract_artifact_value(artifact, "hermes_agent_commit")
    allowlist_commit = hermes_pin.get("commit")
    if not isinstance(allowlist_commit, str) or not allowlist_commit:
        errors.append(f"{_ALLOWLIST_REL}: hermes_pin.commit must be a non-empty string")
    elif artifact_commit != allowlist_commit:
        errors.append(
            "GENESIS_ARTIFACT Hermes commit does not match allowlist "
            f"(artifact={artifact_commit!r}, allowlist={allowlist_commit!r})"
        )

    artifact_allowlist_hash = _extract_artifact_value(artifact, "hermes_tool_allowlist_sha256")
    current_allowlist_hash = sha256_file(allowlist_path)
    if artifact_allowlist_hash != current_allowlist_hash:
        errors.append(
            "GENESIS_ARTIFACT hermes_tool_allowlist_sha256 mismatch "
            f"(artifact={artifact_allowlist_hash!r}, actual={current_allowlist_hash})"
        )

    root_pyproject = repo_root / "pyproject.toml"
    lockfile_candidates = (
        repo_root / "uv.lock",
        repo_root / "poetry.lock",
        repo_root / "requirements.lock",
        repo_root / "pdm.lock",
    )
    pyproject_text = root_pyproject.read_text(encoding="utf-8") if root_pyproject.is_file() else ""
    has_hermes_dependency = "hermes" in pyproject_text.lower() or any(
        p.is_file() and "hermes" in p.read_text(encoding="utf-8").lower()
        for p in lockfile_candidates
    )
    if not has_hermes_dependency:
        notes.append(
            "runtime dependency pin is NOT_YET_SEALED: Hermes is doctrine-pinned, "
            "but no installable Hermes dependency/lockfile entry exists yet"
        )

    return errors, notes


@click.command(name="hermes-runtime")
def hermes_runtime() -> None:
    """Verify Hermes pin, default-deny allowlist, and disabled runtime flags."""

    try:
        repo_root = find_repo_root(Path.cwd())
    except RepoRootNotFound as exc:
        click.echo(f"hermes-runtime: FAIL: {exc}", err=True)
        raise SystemExit(FAIL) from None

    errors, notes = check_hermes_runtime(repo_root)
    if errors:
        for error in errors:
            click.echo(f"hermes-runtime: FAIL: {error}", err=True)
        raise SystemExit(FAIL)

    click.echo("hermes-runtime: OK (Hermes pin, allowlist hash, default-deny flags verified)")
    for note in notes:
        click.echo(f"hermes-runtime: {note}")
    raise SystemExit(OK)
