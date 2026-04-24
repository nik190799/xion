"""`xion-verify ao-handlers` — AO Core handler set doctrine verification.

Property promised. For every `ao-handler-*.yaml` file under `docs/schemas/`:

1. The file parses as valid YAML.
2. The top-level object has the required fields: `handler`, `family`, `schema_version`, `status`, `args`, `state_changes`, `failure_modes`.
3. `family` is one of `{lifecycle, authority, provisioning, sustainability}`.
4. `source_sha256` matches the hash of `docs/04-ARCHITECTURE.md`.
5. `operational_sha256` matches the hash of `docs/28-AO-CORE.md`.

Returns `NOT_YET_SEALED` until Phase 6.1, when the Lua skeleton lands.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click
import yaml

from xion_verify.exit_codes import FAIL, NOT_YET_SEALED, OK
from xion_verify.hashing import sha256_file
from xion_verify.repo import RepoRootNotFound, find_repo_root

_SCHEMAS_DIRNAME = "docs/schemas"
_REQUIRED_META: tuple[str, ...] = (
    "handler",
    "family",
    "schema_version",
    "status",
    "args",
    "state_changes",
    "failure_modes",
    "source_doctrine",
    "source_sha256",
    "operational_doctrine",
    "operational_sha256",
)
_ALLOWED_FAMILIES: frozenset[str] = frozenset({"lifecycle", "authority", "provisioning", "sustainability"})

_EXPECTED_HANDLERS: frozenset[str] = frozenset({
    "commit-state", "attest", "treasury-spend", "registry-update", "spend", "slash-imprint",
    "rotate-authority", "abdicate-tier",
    "provision-relay", "provision-inference", "provision-storage", "provision-bandwidth", "provision-witness",
    "route-slices", "improvement-spend", "reserve-draw", "accept-donation", "enter-hibernation", "exit-hibernation"
})


def _fail(label: str, message: str) -> tuple[int, str]:
    return FAIL, f"{label}: FAIL: {message}"


def _check_one_schema(path: Path, repo_root: Path, arch_hash: str, core_hash: str) -> tuple[int, str]:
    label = f"ao-handlers[{path.relative_to(repo_root).as_posix()}]"

    try:
        raw = path.read_bytes()
    except OSError as exc:
        return _fail(label, f"cannot read: {exc}")

    try:
        data: Any = yaml.safe_load(raw.decode("utf-8"))
    except yaml.YAMLError as exc:
        return _fail(label, f"invalid YAML: {exc}")
    except UnicodeDecodeError as exc:
        return _fail(label, f"not valid UTF-8: {exc}")

    if not isinstance(data, dict):
        return _fail(label, "top-level YAML value must be a mapping")

    missing = [f for f in _REQUIRED_META if f not in data]
    if missing:
        return _fail(label, f"missing required meta fields: {', '.join(missing)}")

    family = data["family"]
    if family not in _ALLOWED_FAMILIES:
        return _fail(
            label,
            f"family must be one of {sorted(_ALLOWED_FAMILIES)}; got {family!r}",
        )

    if data["source_sha256"] != arch_hash:
        return _fail(
            label,
            f"source_sha256 mismatch for docs/04-ARCHITECTURE.md\n"
            f"  expected: {arch_hash}\n"
            f"  actual:   {data['source_sha256']}",
        )

    if data["operational_sha256"] != core_hash:
        return _fail(
            label,
            f"operational_sha256 mismatch for docs/28-AO-CORE.md\n"
            f"  expected: {core_hash}\n"
            f"  actual:   {data['operational_sha256']}",
        )

    return OK, f"{label}: OK"


@click.command(name="ao-handlers")
def verify_ao_handlers() -> None:
    """Verify AO Core handler schemas against doctrine."""
    try:
        repo_root = find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"ao-handlers: FAIL: {exc}", err=True)
        raise click.exceptions.Exit(FAIL)

    schemas_dir = repo_root / _SCHEMAS_DIRNAME
    if not schemas_dir.is_dir():
        click.echo(f"ao-handlers: NOT_YET_SEALED: {schemas_dir} not found")
        raise click.exceptions.Exit(NOT_YET_SEALED)

    arch_path = repo_root / "docs/04-ARCHITECTURE.md"
    core_path = repo_root / "docs/28-AO-CORE.md"

    if not arch_path.is_file() or not core_path.is_file():
        click.echo("ao-handlers: FAIL: doctrine files not found", err=True)
        raise click.exceptions.Exit(FAIL)

    arch_hash = sha256_file(arch_path)
    core_hash = sha256_file(core_path)

    yaml_files = sorted(schemas_dir.glob("ao-handler-*.yaml"))
    if not yaml_files:
        click.echo("ao-handlers: NOT_YET_SEALED: no ao-handler-*.yaml files found")
        raise click.exceptions.Exit(NOT_YET_SEALED)

    found_handlers = set()
    worst_code = OK
    messages: list[str] = []

    for path in yaml_files:
        code, msg = _check_one_schema(path, repo_root, arch_hash, core_hash)
        messages.append(msg)
        if code != OK:
            worst_code = max(worst_code, code)
        
        # Extract handler name from filename
        handler_name = path.stem.replace("ao-handler-", "")
        found_handlers.add(handler_name)

    missing_handlers = _EXPECTED_HANDLERS - found_handlers
    if missing_handlers:
        worst_code = FAIL
        messages.append(f"ao-handlers: FAIL: missing expected handler schemas: {sorted(missing_handlers)}")

    extra_handlers = found_handlers - _EXPECTED_HANDLERS
    if extra_handlers:
        worst_code = FAIL
        messages.append(f"ao-handlers: FAIL: unexpected handler schemas found: {sorted(extra_handlers)}")

    for msg in messages:
        click.echo(msg, err=(worst_code == FAIL and "FAIL" in msg))

    if worst_code == OK:
        # Phase 6.1: Check for Lua skeleton and deploy receipt
        lua_entry = repo_root / "ao/process/xion_core.lua"
        lua_commit = repo_root / "ao/process/handlers/commit_state.lua"
        lua_attest = repo_root / "ao/process/handlers/attest.lua"
        receipt = repo_root / "genesis/AO_DEPLOY_RECEIPT.json"

        missing_lua = []
        if not lua_entry.is_file(): missing_lua.append("ao/process/xion_core.lua")
        if not lua_commit.is_file(): missing_lua.append("ao/process/handlers/commit_state.lua")
        if not lua_attest.is_file(): missing_lua.append("ao/process/handlers/attest.lua")

        if missing_lua:
            click.echo(f"ao-handlers: NOT_YET_SEALED ({len(yaml_files)} handler schema(s) verified, awaiting Lua skeleton: {', '.join(missing_lua)})")
            raise click.exceptions.Exit(NOT_YET_SEALED)

        if not receipt.is_file():
            click.echo(f"ao-handlers: NOT_YET_SEALED ({len(yaml_files)} handler schema(s) verified, Lua skeleton present, awaiting genesis/AO_DEPLOY_RECEIPT.json)")
            raise click.exceptions.Exit(NOT_YET_SEALED)

        click.echo(f"ao-handlers: OK ({len(yaml_files)} handler schema(s) verified, Lua skeleton and deploy receipt present)")
        raise click.exceptions.Exit(OK)
    else:
        click.echo(f"ao-handlers: FAIL ({len(yaml_files)} handler schema(s) checked)", err=True)
        raise click.exceptions.Exit(worst_code)
