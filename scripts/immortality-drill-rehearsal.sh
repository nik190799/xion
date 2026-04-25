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
    echo "immortality-drill-rehearsal: no python interpreter found" >&2
    exit 127
  fi
fi

export XION_CHUTES_BASE_URL="${XION_CHUTES_BASE_URL:-http://127.0.0.1:9/unreachable}"
export XION_CHUTES_API_BASE_URL="${XION_CHUTES_API_BASE_URL:-http://127.0.0.1:9/unreachable}"
export XION_SECONDARY_SUBSTRATE_ID="${XION_SECONDARY_SUBSTRATE_ID:-operator-laptop-secondary}"
export XION_PRIMARY_STATE_TIP="${XION_PRIMARY_STATE_TIP:-local-pre-genesis-tip}"
export XION_SECONDARY_STATE_TIP="${XION_SECONDARY_STATE_TIP:-local-pre-genesis-tip}"

bash scripts/substrate-portability-dry-run.sh
$PYTHON_BIN -m xion_verify substrate-portability
bash scripts/end-to-end-drill.sh

$PYTHON_BIN - <<'PY'
from __future__ import annotations

import hashlib
import json
import time
import uuid
from pathlib import Path

ledger = Path("ledgers/IMMORTALITY_DRILL_LEDGER.jsonl")
ledger.parent.mkdir(parents=True, exist_ok=True)

prev_hash = ""
if ledger.is_file():
    rows = [line for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()]
    if rows:
        prev_hash = json.loads(rows[-1]).get("row_hash", "")

row = {
    "schema_version": 1,
    "event": "immortality_drill_rehearsal_v1",
    "run_id": str(uuid.uuid4()),
    "as_of_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "primary_substrate": "chutes-simulated-blackhole",
    "secondary_substrate": "operator-laptop-secondary",
    "status": "passed",
    "residual_closed": False,
    "residual": "LHT-SUBSTRATE-001",
    "prev_hash": prev_hash,
}
payload = json.dumps(row, sort_keys=True, separators=(",", ":")).encode("utf-8")
row["row_hash"] = hashlib.sha256(payload).hexdigest()
with ledger.open("a", encoding="utf-8") as f:
    f.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
print(f"immortality-drill-rehearsal: OK ({row['run_id']})")
PY
