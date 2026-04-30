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
Exits 5 if the gateway reports 410 Gone for /tx/<id> (phantom or rejected send).
Exits 6 if the tx never becomes HTTP 200 or 202 visible on the gateway within ~180s.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _gateway_tx_status(gateway: str, tx_id: str, *, timeout: float = 20.0) -> int | None:
    """Return HTTP status for GET {gateway}/tx/{tx_id}, or None on network error."""
    url = gateway.rstrip("/") + "/tx/" + tx_id.strip()
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return int(resp.status)
    except urllib.error.HTTPError as exc:
        return int(exc.code)
    except OSError:
        return None


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
    from orchestrator.registry.gateway import (  # noqa: E402
        RelayRegistryPublisherSettings,
        get_relay_registry_publisher,
    )

    jwk = os.environ.get("XION_REGISTRY_WALLET_JWK_PATH", "")
    if not jwk or not Path(jwk).is_file():
        print(
            "publish-relay-registry: set XION_REGISTRY_WALLET_JWK_PATH to a readable JWK file",
            file=sys.stderr,
        )
        return 3
    try:
        publisher = get_relay_registry_publisher(
            RelayRegistryPublisherSettings(backend="arweave")
        )
    except Exception as exc:  # pragma: no cover - import/runtime
        print(f"publish-relay-registry: {exc}", file=sys.stderr)
        return 3

    if os.environ.get("XION_SKIP_AR_BALANCE_CHECK", "").lower() not in ("1", "true", "yes"):
        try:
            import arweave as arw  # type: ignore[import-not-found]

            aw = arw.Wallet(jwk)
            bal_ar = float(aw.balance)
            if bal_ar <= 0:
                print(
                    f"publish-relay-registry: wallet {aw.address} has 0 AR balance; "
                    "fund with AR then re-run (or set XION_SKIP_AR_BALANCE_CHECK=1 at your risk).",
                    file=sys.stderr,
                )
                return 4
        except Exception as exc:
            print(f"publish-relay-registry: could not read Arweave wallet balance: {exc}", file=sys.stderr)
            return 3

    raw = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    submitter = publisher._submitter  # noqa: SLF001 — script owns deploy-time diagnostics
    tx_id = submitter.submit(
        raw,
        {"App-Name": "xion-relay-registry", "Schema-Version": "1", "Xion-Primary-Substrate": "akash"},
    )
    gw = submitter._gateway  # noqa: SLF001 — same gateway the client used for send
    deadline = time.monotonic() + 180.0
    status: int | None = None
    while time.monotonic() < deadline:
        status = _gateway_tx_status(gw, tx_id)
        if status in (200, 202):
            break
        if status == 410:
            print(
                f"publish-relay-registry: gateway {gw}/tx/{tx_id.strip()} returned 410 Gone; "
                "transaction did not land — not writing RELAY_REGISTRY_ARWEAVE_TX.txt "
                "(common when the wallet had no AR or the client reported a phantom id).",
                file=sys.stderr,
            )
            return 5
        time.sleep(4.0)
    else:
        print(
            f"publish-relay-registry: tx {tx_id.strip()} not visible as HTTP 200/202 on {gw} "
            f"(last status={status}); not writing RELAY_REGISTRY_ARWEAVE_TX.txt.",
            file=sys.stderr,
        )
        return 6

    out = root / "ledgers" / "RELAY_REGISTRY_ARWEAVE_TX.txt"
    out.write_text(tx_id.strip() + "\n", encoding="utf-8")
    print(f"publish-relay-registry: Arweave tx {tx_id}")
    print(f"publish-relay-registry: wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
