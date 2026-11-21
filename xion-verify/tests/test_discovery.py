from __future__ import annotations

import hashlib
import json
from pathlib import Path

from xion_verify.commands.discovery import evaluate_discovery
from xion_verify.commands.akash_deploy_discipline import evaluate as evaluate_akash_deploy_discipline
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


def test_discovery_marks_placeholder_public_keys_not_yet_sealed(tmp_path: Path) -> None:
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
                    "endpoint": "https://relay.akash.invalid",
                    "public_key": "ed25519:not-yet-bound",
                    "last_seen_utc_ns": 1,
                },
                {
                    "relay_id": "chutes-secondary",
                    "substrate": "chutes",
                    "endpoint": "https://xion-relay.chutes.ai",
                    "public_key": "ed25519:reference-key",
                    "last_seen_utc_ns": 1,
                },
            ],
        }
    )
    _write_registry(tmp_path, registry)
    code, messages = evaluate_discovery(tmp_path)

    assert code == NOT_YET_SEALED
    assert any("placeholder" in m for m in messages)


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


def test_discovery_no_cloudflare_rejects_cloudflare_endpoint(tmp_path: Path) -> None:
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
                    "endpoint": "https://xion-relay.example.workers.dev",
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

    code, messages = evaluate_discovery(tmp_path, no_cloudflare=True)

    assert code != OK
    assert any("Cloudflare" in message for message in messages)


def test_akash_deploy_discipline_requires_allowlist_and_guard(tmp_path: Path) -> None:
    service_dir = tmp_path / "xion_ops" / "services"
    service_dir.mkdir(parents=True)
    (tmp_path / "genesis").mkdir()
    (service_dir / "akash.py").write_text(
        "provider_allowlist _choose_reachable_provider _provider_ingress_reachable "
        "pre_accept_reachable skip_unreachable_provider_ingress",
        encoding="utf-8",
    )
    (tmp_path / "genesis" / "PROVIDER_ALLOWLIST.json").write_text(
        json.dumps({"providers": [{"provider": "akash1provider"}]}),
        encoding="utf-8",
    )

    assert evaluate_akash_deploy_discipline(tmp_path) == []
