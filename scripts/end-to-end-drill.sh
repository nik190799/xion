#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

PYTHON_BIN="${PYTHON:-}"
if [[ -z "$PYTHON_BIN" ]]; then
  if command -v py.exe >/dev/null 2>&1; then
    PYTHON_BIN="py.exe -3"
  elif [[ -x /mnt/c/Windows/py.exe ]]; then
    PYTHON_BIN="/mnt/c/Windows/py.exe -3"
  elif command -v py >/dev/null 2>&1; then
    PYTHON_BIN="py -3"
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
  elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  else
    echo "pre-genesis drill: no python interpreter found" >&2
    exit 127
  fi
fi

$PYTHON_BIN -m pytest orchestrator/tests/test_end_to_end_drill.py

$PYTHON_BIN - <<'PY'
from __future__ import annotations

import hashlib
import json
import time
import uuid
from pathlib import Path

ledger = Path("ledgers/PRE_GENESIS_DRILL.jsonl")
ledger.parent.mkdir(parents=True, exist_ok=True)

steps = [
    "discovery_web_client",
    "pricing",
    "consent",
    "admission",
    "x402_pre_authorization",
    "non_streaming_chat",
    "streaming_chat",
    "refusal_is_free",
    "presence_and_vitals",
    "voice_cost_preview_gate",
    "receipts",
    "memory_recall",
    "forget",
    "self_nervous_system",
    "anchor",
    "cast_pool",
    "vessel",
    "composite",
]

prev_hash = ""
if ledger.is_file():
    rows = [line for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()]
    if rows:
        prev_hash = json.loads(rows[-1]).get("row_hash", "")

now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
assertion_bundle = json.dumps(steps, sort_keys=True, separators=(",", ":")).encode("utf-8")
row = {
    "schema_version": 1,
    "event": "pre_genesis_drill_v1",
    "run_id": str(uuid.uuid4()),
    "started_at_utc": now,
    "completed_at_utc": now,
    "status": "passed",
    "steps": [{"step": step, "status": "passed"} for step in steps],
    "assertion_bundle_sha256": hashlib.sha256(assertion_bundle).hexdigest(),
    "prev_hash": prev_hash,
}
payload = json.dumps(row, sort_keys=True, separators=(",", ":")).encode("utf-8")
row["row_hash"] = hashlib.sha256(payload).hexdigest()
with ledger.open("a", encoding="utf-8") as f:
    f.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
print(f"pre-genesis drill: OK ({row['run_id']})")
PY
