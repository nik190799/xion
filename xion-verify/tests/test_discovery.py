from __future__ import annotations

import hashlib
import json
from pathlib import Path

from click.testing import CliRunner

from xion_verify.cli import root
from xion_verify.commands.discovery import evaluate_discovery
from xion_verify.exit_codes import NOT_YET_SEALED, OK


def _write_registry(repo: Path, data: dict[str, object]) -> None:
    ledgers = repo / "ledgers"
    ledgers.mkdir()
    (ledgers / "RELAY_REGISTRY.json").write_text(json.dumps(data), encoding="utf-8")


def _with_payload_hash(data: dict[str, object]) -> dict[str, object]:
    body = {key: value for key, value in data.items() if key != "payload_sha256"}
    data["payload_sha256"] = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()
    return data


def test_discovery_keeps_placeholder_repo_registry_unsealed() -> None:
    result = CliRunner().invoke(root, ["discovery"])

    assert result.exit_code == NOT_YET_SEALED, result.output
    assert "placeholder" in result.output


def test_discovery_accepts_populated_registry(tmp_path: Path) -> None:
    registry = _with_payload_hash(
        {
            "schema_version": 1,
            "as_of_utc_ns": 1,
            "discovery_paths": ["arweave_registry", "ao_process", "dns_seed", "akash_secondary"],
            "payload_sha256": "",
            "relays": [
                {
                    "relay_id": "akash-primary",
                    "substrate": "akash",
                    "endpoint": "https://operator-relay.xion.invalid",
                    "public_key": "ed25519:def456",
                    "last_seen_utc_ns": 1,
                },
                {
                    "relay_id": "chutes-secondary",
                    "substrate": "chutes",
                    "endpoint": "https://xion-relay.chutes.ai",
                    "public_key": "ed25519:abc123",
                    "last_seen_utc_ns": 1,
                },
            ],
        }
    )
    _write_registry(tmp_path, registry)

    code, messages = evaluate_discovery(tmp_path)

    assert code == OK
    assert messages == []
