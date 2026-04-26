"""Dependency topology report for SPOF verification."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def dependency_report(repo_root: Path) -> dict[str, Any]:
    registry_path = repo_root / "ledgers" / "RELAY_REGISTRY.json"
    treasury_path = repo_root / "genesis" / "TREASURY_VAULTS.json"
    return {
        "schema_version": 1,
        "dependencies": [
            {"name": "Chutes Relay primary", "tier": "operational", "redundancy": "operator_laptop"},
            {"name": "Operator laptop secondary", "tier": "operational", "redundancy": "chutes"},
            {"name": "Arweave registry", "tier": "discovery", "redundancy": "ao_process,dns_seed"},
            {"name": "AO process", "tier": "constitutional", "redundancy": "state_chain_receipt"},
            {"name": "Cloudflare", "tier": "convenience", "redundancy": "arweave,ao,dns_seed"},
        ],
        "artifacts": {
            "relay_registry_present": registry_path.is_file(),
            "treasury_manifest_present": treasury_path.is_file(),
        },
    }


__all__ = ["dependency_report"]
