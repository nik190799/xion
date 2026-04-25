from __future__ import annotations

import json

from xion_verify.commands.discovery import check_discovery

from orchestrator.registry.arweave_publisher import RelayRegistryPublisher, build_registry_document


def _relay() -> dict:
    return {
        "relay_id": "relay-1",
        "akash_lease_id": "lease-1",
        "public_key": "ed25519:test",
        "last_seen_utc_ns": 1,
    }


def test_registry_document_is_deterministic_for_fixed_time() -> None:
    first = build_registry_document([_relay()], as_of_utc_ns=1)
    second = build_registry_document([_relay()], as_of_utc_ns=1)

    assert first == second
    assert set(first["discovery_paths"]) == {"arweave_registry", "ao_process", "dns_seed"}


def test_registry_publisher_writes_local_document(tmp_path) -> None:
    path = tmp_path / "ledgers" / "RELAY_REGISTRY.json"

    RelayRegistryPublisher().publish_local(path, [_relay()])

    assert json.loads(path.read_text(encoding="utf-8"))["relays"][0]["relay_id"] == "relay-1"


def test_discovery_accepts_registry_with_three_paths(tmp_path) -> None:
    path = tmp_path / "ledgers" / "RELAY_REGISTRY.json"
    RelayRegistryPublisher().publish_local(path, [_relay()])

    assert check_discovery(tmp_path) == []


def test_discovery_rejects_missing_path(tmp_path) -> None:
    ledger_dir = tmp_path / "ledgers"
    ledger_dir.mkdir()
    (ledger_dir / "RELAY_REGISTRY.json").write_text(
        json.dumps({"schema_version": 1, "discovery_paths": ["dns_seed"], "relays": [_relay()]}),
        encoding="utf-8",
    )

    assert any("missing discovery paths" in error for error in check_discovery(tmp_path))
