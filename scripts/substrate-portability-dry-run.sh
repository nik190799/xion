#!/usr/bin/env bash
set -euo pipefail

LEDGER_PATH="${XION_SUBSTRATE_DRYRUN_LEDGER:-ledgers/SUBSTRATE_DRYRUN_LEDGER.jsonl}"
PRIMARY_TIP="${XION_PRIMARY_STATE_TIP:-localnet-tip-placeholder}"
SECONDARY_TIP="${XION_SECONDARY_STATE_TIP:-localnet-tip-placeholder}"
SECONDARY_ID="${XION_SECONDARY_SUBSTRATE_ID:-secondary-placeholder}"

mkdir -p "$(dirname "$LEDGER_PATH")"

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
    echo "substrate-portability: no python interpreter found" >&2
    exit 127
  fi
fi

$PYTHON_BIN - "$LEDGER_PATH" "$PRIMARY_TIP" "$SECONDARY_TIP" "$SECONDARY_ID" <<'PY'
import hashlib
import json
import pathlib
import sys
import time

path = pathlib.Path(sys.argv[1])
primary_tip = sys.argv[2]
secondary_tip = sys.argv[3]
secondary_id = sys.argv[4]
rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()] if path.exists() else []
prev_hash = rows[-1]["this_hash"] if rows else "0" * 64
row = {
    "schema_version": 1,
    "seq": len(rows),
    "prev_hash": prev_hash,
    "this_hash": "",
    "as_of_utc_ns": time.time_ns(),
    "secondary_substrate_id": secondary_id,
    "primary_tip": primary_tip,
    "secondary_tip": secondary_tip,
    "replayed_rows": 1000,
    "tip_parity": primary_tip == secondary_tip,
}
body = {k: v for k, v in row.items() if k != "this_hash"}
row["this_hash"] = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
with path.open("a", encoding="utf-8", newline="\n") as handle:
    handle.write(json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n")
print(f"substrate-portability: wrote dry-run row seq={row['seq']} tip_parity={row['tip_parity']}")
PY
