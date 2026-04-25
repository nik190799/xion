"""`xion-verify discovery` — Relay registry structural discovery check."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import click

from xion_verify.exit_codes import FAIL, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root

_DEFAULT_REGISTRY = "ledgers/RELAY_REGISTRY.json"
_REQUIRED_PATHS = {"arweave_registry", "ao_process", "dns_seed", "laptop_secondary"}


def check_discovery(repo_root: Path, registry_rel: str = _DEFAULT_REGISTRY) -> list[str]:
    path = repo_root / registry_rel
    if not path.is_file():
        return [f"missing Relay registry: {registry_rel}"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"invalid registry JSON: {exc}"]
    errors: list[str] = []
    if data.get("schema_version") != 1:
        errors.append("registry schema_version must be 1")
    paths = set(data.get("discovery_paths", []))
    missing = _REQUIRED_PATHS - paths
    if missing:
        errors.append(f"missing discovery paths: {sorted(missing)}")
    relays = data.get("relays")
    if not isinstance(relays, list) or not relays:
        errors.append("registry must contain at least one relay")
    else:
        for index, relay in enumerate(relays):
            if not isinstance(relay, dict):
                errors.append(f"relay {index}: must be mapping")
                continue
            for field in ("relay_id", "substrate", "endpoint", "public_key", "last_seen_utc_ns"):
                if field not in relay:
                    errors.append(f"relay {index}: missing {field}")
        substrates = {str(relay.get("substrate")) for relay in relays if isinstance(relay, dict)}
        if "chutes" not in substrates:
            errors.append("registry must contain Chutes primary relay")
        if "operator_laptop" not in substrates:
            errors.append("registry must contain operator-laptop secondary relay")
    expected = _payload_hash(data)
    if data.get("payload_sha256") not in {expected, "0" * 64}:
        errors.append("payload_sha256 mismatch")
    return errors


def _payload_hash(data: dict[str, Any]) -> str:
    body = {key: value for key, value in data.items() if key != "payload_sha256"}
    payload = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(payload).hexdigest()


@click.command(name="discovery", help="Verify Relay registry declares three independent discovery paths.")
@click.option("--registry", default=_DEFAULT_REGISTRY, show_default=True, help="Registry path relative to repo root.")
def discovery(registry: str) -> None:
    try:
        repo_root = find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"discovery: FAIL: {exc}", err=True)
        sys.exit(FAIL)
    errors = check_discovery(repo_root, registry)
    if errors:
        for error in errors:
            click.echo(f"discovery: FAIL: {error}", err=True)
        sys.exit(FAIL)
    click.echo("discovery: OK (Relay registry declares Chutes primary, laptop secondary, Arweave, AO, DNS paths)")
    sys.exit(OK)


__all__ = ["check_discovery", "discovery"]
