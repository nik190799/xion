#!/usr/bin/env python3
"""Write genesis/AO_DEPLOY_RECEIPT.json + first STATE_CHAIN row after a localnet seal.

Run from repo root after `aos` spawn, load, and first commit-state. Needs:
  - Tip height 1, state root = SHA-256 of empty (documented in AO_DEPLOY_LOCALNET.md)
  - Optional: query CU to confirm (xion-verify does this).

Example:
  python3 scripts/record_ao_seal_artifacts.py \\
    --process-id <ao.id> \\
    --signer <Owner> \\
    --message-id <inbox State-Committed message id> \\
    --reset-ledger
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

# Strips CSI sequences (chalk colors etc.) — `aos --version` prints
# `\x1b[90m\nAOS Client Version: 2.0.11. 2025\x1b[0m`, and we don't want
# raw escape codes baked into a verifier-readable receipt.
_ANSI_CSI_RE = re.compile(r"\x1B\[[0-9;]*[A-Za-z]")

_REPO = Path(__file__).resolve().parent.parent
for _p in (_REPO, _REPO / "xion-verify" / "src"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from xion_verify.hashing import sha256_file  # noqa: E402

from orchestrator.ao_core.ledger import (  # noqa: E402
    StateChainRecord,
    ZERO_HASH,
    append,
    verify_chain,
)

# First commit: empty-byte SHA-256, prev on-chain root = 64 zero hex (StateTip genesis in main.lua)
_FIRST_STATE_ROOT = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
_PREV_STATE_ROOT = "0" * 64


def _aos_version() -> str:
    try:
        raw = subprocess.check_output(["aos", "--version"], text=True, timeout=10)
    except (OSError, subprocess.CalledProcessError) as e:
        raise SystemExit(f"record_ao_seal_artifacts: could not run aos --version: {e}") from e
    return _ANSI_CSI_RE.sub("", raw).strip()


def _write_receipt(
    out: Path,
    *,
    process_id: str,
    signer_address: str,
    lua_sha: str,
    aos_version: str,
    timestamp: int,
    first_commit_id: str,
) -> None:
    data = {
        "status": "deployed",
        "process_id": process_id,
        "timestamp": timestamp,
        "network": "testnet",
        "substrate": "localnet",
        "signer_address": signer_address,
        "lua_source_sha256": lua_sha,
        "aos_version": aos_version,
        "first_commit_state_message_id": first_commit_id,
    }
    out.write_text(json.dumps(data, indent=4) + "\n", encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--process-id", required=True)
    p.add_argument("--signer", required=True, help="Owner / signer (aos `Owner` in process)")
    p.add_argument("--message-id", required=True, help="Inbox id of the State-Committed reply")
    p.add_argument(
        "--correlation-id",
        default="",
        help="Optional; default phase61b_{unix_ts}",
    )
    p.add_argument("--reset-ledger", action="store_true", help="Delete ledgers/STATE_CHAIN_LEDGER.jsonl then append row 0")
    p.add_argument(
        "--skip-receipt",
        action="store_true",
        help="Only (re)write STATE_CHAIN row",
    )
    args = p.parse_args()

    lua = _REPO / "ao" / "core" / "main.lua"
    if not lua.is_file():
        print("record_ao_seal_artifacts: ao/core/main.lua not found", file=sys.stderr)
        return 1
    receipt_path = _REPO / "genesis" / "AO_DEPLOY_RECEIPT.json"
    ledger_path = _REPO / "ledgers" / "STATE_CHAIN_LEDGER.jsonl"
    now = int(time.time())
    correllation = args.correlation_id or f"phase61b_{now}"
    av = _aos_version()
    lua_sha = sha256_file(lua)

    if not args.skip_receipt:
        _write_receipt(
            receipt_path,
            process_id=args.process_id,
            signer_address=args.signer,
            lua_sha=lua_sha,
            aos_version=av,
            timestamp=now,
            first_commit_id=args.message_id,
        )

    if args.reset_ledger and ledger_path.is_file():
        ledger_path.unlink()

    record = StateChainRecord(
        correlation_id=correllation,
        height=1,
        state_root_sha256=_FIRST_STATE_ROOT,
        prev_state_root_sha256=_PREV_STATE_ROOT,
        ao_process_id=args.process_id,
        ao_message_id=args.message_id,
        committed_by=args.signer,
        committed_at_unix=now,
    )
    row = append(ledger_path, record)
    try:
        n, _ = verify_chain(ledger_path)
    except Exception as exc:  # noqa: BLE001
        print(f"record_ao_seal_artifacts: hash chain: {exc}", file=sys.stderr)
        return 1
    if n < 1:
        print("record_ao_seal_artifacts: FAIL: no rows in ledger", file=sys.stderr)
        return 1
    print(f"record_ao_seal_artifacts: wrote {receipt_path} and ledger row seq={row['seq']} this_hash={row['this_hash'][:16]}…")
    print("Next:  export XION_AO_GATEWAY_URL=http://localhost:4004")
    print("        xion-verify ao-handlers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
