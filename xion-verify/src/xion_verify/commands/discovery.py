"""`xion-verify discovery` — Relay registry structural discovery check."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import click

from xion_verify.exit_codes import FAIL, NOT_YET_SEALED, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root

_DEFAULT_REGISTRY = "ledgers/RELAY_REGISTRY.json"
_REQUIRED_PATHS = {"arweave_registry", "ao_process", "dns_seed", "akash_secondary"}


def check_discovery(repo_root: Path, registry_rel: str = _DEFAULT_REGISTRY) -> list[str]:
    _code, messages = evaluate_discovery(repo_root, registry_rel=registry_rel)
    return messages


def evaluate_discovery(repo_root: Path, registry_rel: str = _DEFAULT_REGISTRY) -> tuple[int, list[str]]:
    path = repo_root / registry_rel
    if not path.is_file():
        return NOT_YET_SEALED, [f"missing Relay registry: {registry_rel}"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return FAIL, [f"invalid registry JSON: {exc}"]
    errors: list[str] = []
    unsealed: list[str] = []
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
            endpoint = str(relay.get("endpoint", ""))
            public_key = str(relay.get("public_key", ""))
            if "example" in endpoint or endpoint.startswith("http://127.0.0.1"):
                unsealed.append(f"relay {index}: endpoint is placeholder/local")
            if "not-yet" in public_key or "reference" in public_key:
                unsealed.append(f"relay {index}: public_key is placeholder")
        if len(relays) < 2:
            errors.append("registry must list at least two relays (Akash primary, Chutes secondary)")
        else:
            r0, r1 = relays[0], relays[1]
            if not isinstance(r0, dict) or not isinstance(r1, dict):
                pass  # already flagged above
            elif str(r0.get("substrate")) != "akash":
                errors.append("relays[0] must be Akash (genesis primary)")
            elif str(r1.get("substrate")) != "chutes":
                errors.append("relays[1] must be Chutes (genesis secondary)")
    expected = _payload_hash(data)
    if data.get("payload_sha256") == "0" * 64:
        unsealed.append("payload_sha256 is placeholder")
    elif data.get("payload_sha256") != expected:
        errors.append("payload_sha256 mismatch")
    if errors:
        return FAIL, errors
    if unsealed:
        return NOT_YET_SEALED, unsealed
    return OK, []


def _payload_hash(data: dict[str, Any]) -> str:
    body = {key: value for key, value in data.items() if key != "payload_sha256"}
    payload = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(payload).hexdigest()


@click.command(
    name="discovery",
    help="Verify Relay registry declares discovery paths and genesis row order (Akash primary, Chutes secondary).",
)
@click.option("--registry", default=_DEFAULT_REGISTRY, show_default=True, help="Registry path relative to repo root.")
def discovery(registry: str) -> None:
    try:
        repo_root = find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"discovery: FAIL: {exc}", err=True)
        sys.exit(FAIL)
    code, messages = evaluate_discovery(repo_root, registry)
    if messages:
        label = "NOT_YET_SEALED" if code == NOT_YET_SEALED else "FAIL"
        for message in messages:
            click.echo(f"discovery: {label}: {message}", err=(code == FAIL))
        sys.exit(code)
    click.echo("discovery: OK (Relay registry declares Akash primary, Chutes secondary, Arweave, AO, DNS paths)")
    sys.exit(OK)


__all__ = ["check_discovery", "discovery", "evaluate_discovery"]
