#!/usr/bin/env bash
set -euo pipefail

# Doctrine: Akash primary, Chutes secondary. A full run must set or source
# Chutes health credentials and deployment evidence (see docs/runbooks/AKASH_RELAY_DEPLOY.md).
# For offline substrate-portability ledger mechanics only, override with
# XION_SECONDARY_SUBSTRATE_ID=operator-laptop-secondary.

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

SECRETS="${XION_CHUTES_SECRETS_FILE:-/mnt/c/Users/16823/Documents/xion/xion-secrets/chutes.env}"
if [[ -f "$SECRETS" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$SECRETS"
  set +a
fi

export XION_CHUTES_BASE_URL="${XION_CHUTES_BASE_URL:-http://127.0.0.1:9/unreachable}"
export XION_CHUTES_API_BASE_URL="${XION_CHUTES_API_BASE_URL:-http://127.0.0.1:9/unreachable}"
export XION_SECONDARY_SUBSTRATE_ID="${XION_SECONDARY_SUBSTRATE_ID:-chutes-d3-standby}"
export XION_SECONDARY_PROVIDER="${XION_SECONDARY_PROVIDER:-chutes}"
CHUTE_URL="${CHUTE_PUBLIC_URL:-https://nikhilkadalge-xion-relay-pre-genesis-d3.chutes.ai}"
export XION_SECONDARY_HEALTH_URL="${XION_SECONDARY_HEALTH_URL:-${CHUTE_URL}/health}"
export XION_DEPLOYMENT_EVIDENCE="${XION_DEPLOYMENT_EVIDENCE:-chutes://89866bfc-5ddd-5382-b887-116d8901808f/98f0cdf3-e8a0-461d-8a75-a4d3240e0389}"
export XION_SECONDARY_HEALTH_BEARER="${XION_SECONDARY_HEALTH_BEARER:-${CHUTES_API_KEY:-}}"
export XION_PRIMARY_STATE_TIP="${XION_PRIMARY_STATE_TIP:-local-pre-genesis-tip}"
export XION_SECONDARY_STATE_TIP="${XION_SECONDARY_STATE_TIP:-local-pre-genesis-tip}"

bash scripts/substrate-portability-dry-run.sh
$PYTHON_BIN -m xion_verify substrate-portability
bash scripts/end-to-end-drill.sh
printf '{"source":"immortality-drill-rehearsal","status":"drill_checks_passed","details":{"secondary_substrate":"%s","deployment_evidence":"%s"}}' "$XION_SECONDARY_SUBSTRATE_ID" "$XION_DEPLOYMENT_EVIDENCE" | $PYTHON_BIN -m orchestrator.status

$PYTHON_BIN - <<'PY'
from __future__ import annotations

import hashlib
import json
import os
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
    "primary_substrate": "akash-simulated-blackhole",
    "secondary_substrate": os.environ.get("XION_SECONDARY_SUBSTRATE_ID", "akash-mainnet-secondary"),
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
