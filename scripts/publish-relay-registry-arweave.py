#!/usr/bin/env python3
"""Publish ledgers/RELAY_REGISTRY.json to Arweave using the operator JWK (env).

Requires: pip install arweave (arweave-python-client), and
  XION_REGISTRY_WALLET_JWK_PATH pointing to a JWK file.

The payload is the canonical minified document (including payload_sha256) so
xion-verify discovery can re-hash the same way as the on-disk file.

Exits 2 if the file is missing, hash mismatch, or Akash primary endpoint is still
a placeholder (override with XION_ALLOW_PENDING_AKASH_ENDPOINT=1). Exits 3 if
wallet/client not configured. Exits 4 if the Arweave wallet balance is zero (no
AR to pay storage). Set XION_SKIP_AR_BALANCE_CHECK=1 to override (not recommended).
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _main() -> int:
    root = _repo_root()
    reg = root / "ledgers" / "RELAY_REGISTRY.json"
    if not reg.is_file():
        print(f"publish-relay-registry: missing {reg}", file=sys.stderr)
        return 2
    data = json.loads(reg.read_text(encoding="utf-8"))
    body = {k: v for k, v in data.items() if k != "payload_sha256"}
    expect = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    if data.get("payload_sha256") != expect:
        print("publish-relay-registry: payload_sha256 mismatch with file contents", file=sys.stderr)
        return 2
    relays = data.get("relays") or []
    if (
        len(relays) > 0
        and str(relays[0].get("substrate")) == "akash"
        and "pending" in str(relays[0].get("endpoint", ""))
        and os.environ.get("XION_ALLOW_PENDING_AKASH_ENDPOINT", "").lower() not in ("1", "true", "yes")
    ):
        print(
            "publish-relay-registry: relays[0] Akash endpoint still looks like a placeholder; "
            "set a real https://lease:port (see closeout-genesis-akash-primary-wsl.sh) "
            "or set XION_ALLOW_PENDING_AKASH_ENDPOINT=1 to override.",
            file=sys.stderr,
        )
        return 2

    sys.path.insert(0, str(root))
    from orchestrator.registry.arweave_publisher import (  # noqa: E402
        ArweaveRegistrySubmitter,
    )

    jwk = os.environ.get("XION_REGISTRY_WALLET_JWK_PATH", "")
    if not jwk or not Path(jwk).is_file():
        print(
            "publish-relay-registry: set XION_REGISTRY_WALLET_JWK_PATH to a readable JWK file",
            file=sys.stderr,
        )
        return 3
    try:
        submitter = ArweaveRegistrySubmitter()
    except Exception as exc:  # pragma: no cover - import/runtime
        print(f"publish-relay-registry: {exc}", file=sys.stderr)
        return 3

    if os.environ.get("XION_SKIP_AR_BALANCE_CHECK", "").lower() not in ("1", "true", "yes"):
        try:
            import arweave as arw  # type: ignore[import-not-found]

            aw = arw.Wallet(jwk)
            bal = int(aw.balance)
            if bal <= 0:
                print(
                    f"publish-relay-registry: wallet {aw.address} has 0 winston balance; "
                    "fund with AR then re-run (or set XION_SKIP_AR_BALANCE_CHECK=1 at your risk).",
                    file=sys.stderr,
                )
                return 4
        except Exception as exc:
            print(f"publish-relay-registry: could not read Arweave wallet balance: {exc}", file=sys.stderr)
            return 3

    raw = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    tx_id = submitter.submit(
        raw,
        {"App-Name": "xion-relay-registry", "Schema-Version": "1", "Xion-Primary-Substrate": "akash"},
    )
    out = root / "ledgers" / "RELAY_REGISTRY_ARWEAVE_TX.txt"
    out.write_text(tx_id.strip() + "\n", encoding="utf-8")
    print(f"publish-relay-registry: Arweave tx {tx_id}")
    print(f"publish-relay-registry: wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
