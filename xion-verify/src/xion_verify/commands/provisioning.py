"""Verify the AO provisioning handler family.

Property promised. Xion-initiated provisioning actions have a concrete AO event
surface before any autonomous deployment story depends on them. This command is
the narrow verifier for the five `provision-*` handlers; `ao-handlers` remains
the broader 20-handler gate.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import click
import yaml

from xion_verify.exit_codes import FAIL, OK
from xion_verify.hashing import sha256_file
from xion_verify.repo import RepoRootNotFound, find_repo_root

_PROVISIONING_HANDLERS: tuple[str, ...] = (
    "provision-relay",
    "provision-inference",
    "provision-storage",
    "provision-bandwidth",
    "provision-witness",
)


def _fail(message: str) -> None:
    click.echo(f"provisioning: FAIL: {message}", err=True)
    raise click.exceptions.Exit(FAIL)


def _schema(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        _fail(f"cannot read {path.as_posix()}: {exc}")
    if not isinstance(data, dict):
        _fail(f"{path.as_posix()} must be a YAML mapping")
    return data


@click.command(name="provisioning")
def provisioning() -> None:
    """Verify the five AO `provision-*` handlers are canonical and resealed."""
    try:
        repo_root = find_repo_root()
    except RepoRootNotFound as exc:
        _fail(str(exc))

    lua_path = repo_root / "ao" / "core" / "main.lua"
    receipt_path = repo_root / "genesis" / "AO_DEPLOY_RECEIPT.json"
    if not lua_path.is_file():
        _fail("ao/core/main.lua not found")
    if not receipt_path.is_file():
        _fail("genesis/AO_DEPLOY_RECEIPT.json not found")

    try:
        lua_source = lua_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        _fail(f"cannot read ao/core/main.lua: {exc}")
    registered = set(re.findall(r'Handlers\.add\(\s*"([^"]+)"', lua_source))

    for handler in _PROVISIONING_HANDLERS:
        schema_path = repo_root / "docs" / "schemas" / f"ao-handler-{handler}.yaml"
        if not schema_path.is_file():
            _fail(f"missing schema {schema_path.relative_to(repo_root).as_posix()}")
        data = _schema(schema_path)
        if data.get("handler") != handler:
            _fail(f"{schema_path.name} handler field is {data.get('handler')!r}, expected {handler!r}")
        if data.get("family") != "provisioning":
            _fail(f"{schema_path.name} family is {data.get('family')!r}, expected 'provisioning'")
        if data.get("status") != "canonical":
            _fail(f"{schema_path.name} status is {data.get('status')!r}, expected 'canonical'")
        args = data.get("args")
        if not isinstance(args, list) or not args:
            _fail(f"{schema_path.name} must declare non-empty args")
        if any(isinstance(arg, dict) and arg.get("name") == "dummy_arg" for arg in args):
            _fail(f"{schema_path.name} still contains placeholder dummy_arg")
        if handler not in registered:
            _fail(f"{handler} schema is canonical but ao/core/main.lua has no Handlers.add registration")

    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        _fail(f"cannot read genesis/AO_DEPLOY_RECEIPT.json: {exc}")
    if not isinstance(receipt, dict):
        _fail("genesis/AO_DEPLOY_RECEIPT.json must be a JSON object")
    if receipt.get("status") == "placeholder":
        _fail("AO_DEPLOY_RECEIPT.json is still a placeholder; provisioning handlers are not resealed")
    current_lua_hash = sha256_file(lua_path)
    if receipt.get("lua_source_sha256") != current_lua_hash:
        _fail("AO_DEPLOY_RECEIPT.json lua_source_sha256 does not match current ao/core/main.lua")

    click.echo(
        "provisioning: OK "
        f"({len(_PROVISIONING_HANDLERS)} provision-* handlers canonical, schemas concrete, "
        f"lua hash resealed on substrate={receipt.get('substrate')})"
    )
    raise click.exceptions.Exit(OK)
