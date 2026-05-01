#!/usr/bin/env python3
"""Publish the finalized Genesis Artifact and genesis ledger tips to Arweave.

This script deliberately refuses draft artifacts. `genesis/GENESIS_ARTIFACT.md`
must have its placeholder section removed and all `<<...>>` placeholders
resolved before the one-way Arweave write is allowed.
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
from typing import Any


DEFAULT_GATEWAY = "https://arweave.net"


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _gateway_tx_status(gateway: str, tx_id: str, *, timeout: float = 20.0) -> int | None:
    url = gateway.rstrip("/") + "/tx/" + tx_id.strip()
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return int(resp.status)
    except urllib.error.HTTPError as exc:
        return int(exc.code)
    except OSError:
        return None


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _assert_final_genesis_artifact(path: Path) -> bytes:
    if not path.is_file():
        raise ValueError(f"missing {path}")
    payload = path.read_bytes()
    text = payload.decode("utf-8")
    if "## 0. Instructions Before Commit" in text:
        raise ValueError("GENESIS_ARTIFACT.md still contains § 0 instructions")
    if "<<" in text or ">>" in text:
        raise ValueError("GENESIS_ARTIFACT.md still contains unresolved placeholders")
    if "OPERATOR_SIGNATURE" in text:
        raise ValueError("GENESIS_ARTIFACT.md still appears unsigned")
    return payload


def _ledger_tip(root: Path, filename: str) -> dict[str, Any]:
    path = root / filename
    rows: list[dict[str, Any]] = []
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    tip = rows[-1].get("this_hash") if rows else "0" * 64
    return {
        "schema_version": 1,
        "ledger": filename,
        "row_count": len(rows),
        "tip_hash": tip,
        "ledger_sha256": _sha256(path.read_bytes()) if path.is_file() else None,
        "genesis_state_height": 0,
    }


def _wallet(jwk_path: str):
    try:
        import arweave  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError("install arweave-python-client in .venv-arweave") from exc
    return arweave, arweave.Wallet(jwk_path)


def _send_payload(arweave_module, wallet, payload: bytes, tags: dict[str, str]) -> str:
    tx = arweave_module.Transaction(wallet, data=payload)
    for key, value in tags.items():
        tx.add_tag(key, value)
    tx.sign()
    tx.send()
    return str(tx.id)


def _await_visible(gateway: str, tx_id: str) -> int:
    deadline = time.monotonic() + 180.0
    status: int | None = None
    while time.monotonic() < deadline:
        status = _gateway_tx_status(gateway, tx_id)
        if status in (200, 202):
            return 0
        if status == 410:
            print(f"publish-genesis-artifact: tx {tx_id.strip()} returned 410 Gone", file=sys.stderr)
            return 5
        time.sleep(4.0)
    print(
        f"publish-genesis-artifact: tx {tx_id.strip()} not visible as HTTP 200/202 "
        f"(last status={status})",
        file=sys.stderr,
    )
    return 6


def _main() -> int:
    root = _repo_root()
    artifact = root / "genesis" / "GENESIS_ARTIFACT.md"
    gateway = os.environ.get("XION_GENESIS_ARWEAVE_GATEWAY", DEFAULT_GATEWAY)
    jwk_path = os.environ.get("XION_GENESIS_WALLET_JWK_PATH") or os.environ.get("XION_REGISTRY_WALLET_JWK_PATH")

    try:
        artifact_payload = _assert_final_genesis_artifact(artifact)
    except (OSError, ValueError) as exc:
        print(f"publish-genesis-artifact: REFUSE: {exc}", file=sys.stderr)
        return 2

    if not jwk_path or not Path(jwk_path).is_file():
        print(
            "publish-genesis-artifact: set XION_GENESIS_WALLET_JWK_PATH or "
            "XION_REGISTRY_WALLET_JWK_PATH to a readable JWK file",
            file=sys.stderr,
        )
        return 3

    try:
        arweave_module, wallet = _wallet(jwk_path)
        if os.environ.get("XION_SKIP_AR_BALANCE_CHECK", "").lower() not in ("1", "true", "yes"):
            if float(wallet.balance) <= 0:
                print(f"publish-genesis-artifact: wallet {wallet.address} has 0 AR", file=sys.stderr)
                return 4
    except Exception as exc:
        print(f"publish-genesis-artifact: could not initialize Arweave wallet: {exc}", file=sys.stderr)
        return 3

    artifact_tx = _send_payload(
        arweave_module,
        wallet,
        artifact_payload,
        {
            "App-Name": "xion-genesis",
            "Xion-Artifact": "GENESIS_ARTIFACT",
            "Content-Type": "text/markdown",
            "Xion-Genesis-State-Height": "0",
            "Xion-Artifact-Sha256": _sha256(artifact_payload),
        },
    )
    status = _await_visible(gateway, artifact_tx)
    if status != 0:
        return status

    tip_txs: dict[str, str] = {}
    for ledger_name in ("SAFETY_LEDGER.jsonl", "PAYMENT_LEDGER.jsonl"):
        tip = _ledger_tip(root, ledger_name)
        payload = json.dumps(tip, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        tx_id = _send_payload(
            arweave_module,
            wallet,
            payload,
            {
                "App-Name": "xion-genesis-ledger-tip",
                "Xion-Artifact": "GENESIS_LEDGER_TIP",
                "Content-Type": "application/json",
                "Xion-Ledger": ledger_name,
                "Xion-Genesis-State-Height": "0",
            },
        )
        status = _await_visible(gateway, tx_id)
        if status != 0:
            return status
        tip_txs[ledger_name] = tx_id.strip()

    out = root / "genesis" / "GENESIS_ARWEAVE_TX.txt"
    lines = [
        f"genesis_artifact_sha256={_sha256(artifact_payload)}",
        f"genesis_artifact_arweave_tx={artifact_tx.strip()}",
    ]
    for ledger_name, tx_id in sorted(tip_txs.items()):
        lines.append(f"{ledger_name.lower().replace('.', '_')}_arweave_tx={tx_id}")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"publish-genesis-artifact: artifact tx {artifact_tx.strip()}")
    print(f"publish-genesis-artifact: wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
