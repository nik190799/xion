#!/usr/bin/env python3
"""Generate two Ed25519 keypairs and write public keys into ledgers/RELAY_REGISTRY.json.

Private key material is written only to secrets/relay_registry_ed25519.json (gitignored).
Recomputes payload_sha256 and bumps as_of_utc_ns.

Run from repo root:
  python scripts/gen-relay-registry-ed25519-pubkeys.py
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _pub_hex(priv: Ed25519PrivateKey) -> str:
    raw = priv.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return "ed25519:" + raw.hex()


def _priv_seed_hex(priv: Ed25519PrivateKey) -> str:
    return priv.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    ).hex()


def main() -> None:
    root = _repo_root()
    reg_path = root / "ledgers" / "RELAY_REGISTRY.json"
    data = json.loads(reg_path.read_text(encoding="utf-8"))
    relays = data.get("relays")
    if not isinstance(relays, list) or len(relays) < 2:
        raise SystemExit("registry must have at least two relays")
    k0 = Ed25519PrivateKey.generate()
    k1 = Ed25519PrivateKey.generate()
    relays[0]["public_key"] = _pub_hex(k0)
    relays[1]["public_key"] = _pub_hex(k1)
    data["as_of_utc_ns"] = time.time_ns()
    body = {k: v for k, v in data.items() if k != "payload_sha256"}
    data["payload_sha256"] = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    reg_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    sec_dir = root / "secrets"
    sec_dir.mkdir(exist_ok=True)
    sec_path = sec_dir / "relay_registry_ed25519.json"
    sec_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "relay_id_akash_primary": relays[0].get("relay_id"),
                "relay_id_chutes_secondary": relays[1].get("relay_id"),
                "akash_primary_ed25519_seed_hex": _priv_seed_hex(k0),
                "chutes_secondary_ed25519_seed_hex": _priv_seed_hex(k1),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print("updated", reg_path)
    print("wrote private material (gitignored) to", sec_path)
    print("akash public_key", relays[0]["public_key"])
    print("chutes public_key", relays[1]["public_key"])


if __name__ == "__main__":
    main()
