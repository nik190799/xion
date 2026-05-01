#!/usr/bin/env python3
"""Publish the 2026 treasury audit report and Inv-18 ratification row to Arweave.

Property: a third party can fetch the exact pre-Genesis audit and ratification
evidence from permanent storage before mainnet deployment.

Invariants touched: strengthens Invariant 16 (treasury composition) and
Invariant 18 (voice sovereignty floor) evidence. It does not grant spend or
governance authority.

Verification: refuses a non-PASSED audit, refuses an unreadable or zero-balance
wallet unless explicitly overridden, waits for Arweave gateway visibility, and
writes the resulting tx ids to `docs/audits/treasury-2026-report.arweave-tx.txt`.

Deprecation: a future audit vintage should add a new dated report and tx record
rather than mutating this evidence file.

Exits:
  2: missing/invalid evidence
  3: wallet/client not configured
  4: wallet has zero AR
  5: gateway reports 410 Gone
  6: tx not visible before timeout
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


AUDIT_SIGNOFF_HASH = "8f4e22b10a9c8b7365d9f018a7c645391e8bc27f7a14e9182d3e912389a0b12c"
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


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _read_ratified_inv18_row(root: Path) -> dict[str, Any]:
    ledger = root / "ledgers" / "AMENDMENT_LEDGER.jsonl"
    if not ledger.is_file():
        raise ValueError(f"missing {ledger}")
    for line in ledger.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if (
            row.get("proposal_path") == "docs/proposals/INVARIANT-18-VOICE-SOVEREIGNTY-FLOOR.md"
            and row.get("status") == "ratified"
            and int(row.get("reflection_window_days_observed", 0)) >= int(row.get("reflection_window_days_required", 14))
        ):
            return row
    raise ValueError("no ratified Invariant 18 amendment row found")


def _assert_audit_passed(report: Path) -> bytes:
    if not report.is_file():
        raise ValueError(f"missing {report}")
    payload = report.read_bytes()
    text = payload.decode("utf-8")
    if "**Status:** PASSED." not in text:
        raise ValueError("treasury audit report is not marked PASSED")
    if AUDIT_SIGNOFF_HASH not in text:
        raise ValueError("treasury audit report is missing the expected sign-off hash")
    return payload


def _wallet(jwk_path: str):
    try:
        import arweave  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError(
            "publish-treasury-audit: install arweave-python-client in .venv-arweave"
        ) from exc
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
            print(
                f"publish-treasury-audit: gateway {gateway}/tx/{tx_id.strip()} returned 410 Gone; "
                "transaction did not land.",
                file=sys.stderr,
            )
            return 5
        time.sleep(4.0)
    print(
        f"publish-treasury-audit: tx {tx_id.strip()} not visible as HTTP 200/202 on {gateway} "
        f"(last status={status}).",
        file=sys.stderr,
    )
    return 6


def _main() -> int:
    root = _repo_root()
    report = root / "docs" / "audits" / "treasury-2026-report.md"
    out = root / "docs" / "audits" / "treasury-2026-report.arweave-tx.txt"
    gateway = os.environ.get("XION_AUDIT_ARWEAVE_GATEWAY", DEFAULT_GATEWAY)
    jwk_path = os.environ.get("XION_REGISTRY_WALLET_JWK_PATH") or os.environ.get("XION_AUDIT_WALLET_JWK_PATH")

    try:
        audit_payload = _assert_audit_passed(report)
        inv18_row = _read_ratified_inv18_row(root)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"publish-treasury-audit: {exc}", file=sys.stderr)
        return 2

    if not jwk_path or not Path(jwk_path).is_file():
        print(
            "publish-treasury-audit: set XION_REGISTRY_WALLET_JWK_PATH or "
            "XION_AUDIT_WALLET_JWK_PATH to a readable JWK file",
            file=sys.stderr,
        )
        return 3

    try:
        arweave_module, wallet = _wallet(jwk_path)
        if os.environ.get("XION_SKIP_AR_BALANCE_CHECK", "").lower() not in ("1", "true", "yes"):
            bal_ar = float(wallet.balance)
            if bal_ar <= 0:
                print(
                    f"publish-treasury-audit: wallet {wallet.address} has 0 AR balance; fund it first "
                    "(or set XION_SKIP_AR_BALANCE_CHECK=1 at your risk).",
                    file=sys.stderr,
                )
                return 4
    except Exception as exc:
        print(f"publish-treasury-audit: could not initialize Arweave wallet: {exc}", file=sys.stderr)
        return 3

    audit_tx = _send_payload(
        arweave_module,
        wallet,
        audit_payload,
        {
            "App-Name": "xion-treasury-audit",
            "Xion-Artifact": "TREASURY_AUDIT_REPORT",
            "Schema-Version": "1",
            "Content-Type": "text/markdown",
            "Xion-Audit-Signoff-Sha256": AUDIT_SIGNOFF_HASH,
        },
    )
    audit_status = _await_visible(gateway, audit_tx)
    if audit_status != 0:
        return audit_status

    inv18_payload = json.dumps(inv18_row, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    inv18_tx = _send_payload(
        arweave_module,
        wallet,
        inv18_payload,
        {
            "App-Name": "xion-amendment-ledger",
            "Xion-Artifact": "AMENDMENT_LEDGER_ROW",
            "Schema-Version": "1",
            "Content-Type": "application/json",
            "Xion-Amendment-Target": "Invariant-18",
            "Xion-Amendment-Status": "ratified",
        },
    )
    inv18_status = _await_visible(gateway, inv18_tx)
    if inv18_status != 0:
        return inv18_status

    lines = [
        "# Treasury Audit Arweave Evidence",
        "",
        f"treasury_audit_report_sha256={_sha256_bytes(audit_payload)}",
        f"treasury_audit_arweave_tx={audit_tx.strip()}",
        f"invariant_18_ratification_row_sha256={_sha256_bytes(inv18_payload)}",
        f"invariant_18_ratification_arweave_tx={inv18_tx.strip()}",
        "",
    ]
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"publish-treasury-audit: audit tx {audit_tx.strip()}")
    print(f"publish-treasury-audit: invariant-18 tx {inv18_tx.strip()}")
    print(f"publish-treasury-audit: wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
