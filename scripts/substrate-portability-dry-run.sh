#!/usr/bin/env bash
set -euo pipefail

LEDGER_PATH="${XION_SUBSTRATE_DRYRUN_LEDGER:-ledgers/SUBSTRATE_DRYRUN_LEDGER.jsonl}"
PRIMARY_TIP="${XION_PRIMARY_STATE_TIP:-localnet-tip-placeholder}"
SECONDARY_TIP="${XION_SECONDARY_STATE_TIP:-localnet-tip-placeholder}"
SECONDARY_ID="${XION_SECONDARY_SUBSTRATE_ID:-secondary-placeholder}"
SECONDARY_PROVIDER="${XION_SECONDARY_PROVIDER:-}"
SECONDARY_HEALTH_URL="${XION_SECONDARY_HEALTH_URL:-}"
DEPLOYMENT_EVIDENCE="${XION_DEPLOYMENT_EVIDENCE:-}"
REPLAYED_ROWS="${XION_REPLAYED_ROWS:-1000}"

mkdir -p "$(dirname "$LEDGER_PATH")"

lower_secondary_id="$(printf '%s' "$SECONDARY_ID" | tr '[:upper:]' '[:lower:]')"
is_non_laptop_secondary=0
case "$lower_secondary_id" in
  akash*|aleph*|chutes*)
    is_non_laptop_secondary=1
    ;;
esac

health_status_code=""
health_sha256=""
if [[ "$is_non_laptop_secondary" -eq 1 ]]; then
  if [[ -z "$SECONDARY_HEALTH_URL" ]]; then
    echo "substrate-portability: XION_SECONDARY_HEALTH_URL is required for non-laptop secondary '$SECONDARY_ID'" >&2
    exit 2
  fi
  if [[ -z "$DEPLOYMENT_EVIDENCE" ]]; then
    echo "substrate-portability: XION_DEPLOYMENT_EVIDENCE is required for non-laptop secondary '$SECONDARY_ID'" >&2
    exit 2
  fi
  if ! command -v curl >/dev/null 2>&1; then
    echo "substrate-portability: curl is required to verify secondary health URL" >&2
    exit 127
  fi
  body_file="$(mktemp)"
  trap 'rm -f "$body_file"' EXIT
  curl_args=( -sS -o "$body_file" -w "%{http_code}" )
  if [[ -n "${XION_SECONDARY_HEALTH_BEARER:-}" ]]; then
    curl_args+=( -H "Authorization: Bearer $XION_SECONDARY_HEALTH_BEARER" )
  fi
  if [[ "${XION_SECONDARY_HEALTH_CURL_INSECURE:-0}" == "1" ]]; then
    curl_args+=( -k )
  fi
  health_status_code="$(curl "${curl_args[@]}" "$SECONDARY_HEALTH_URL")"
  case "$health_status_code" in
    2*) ;;
    *)
      echo "substrate-portability: secondary health URL returned HTTP $health_status_code: $SECONDARY_HEALTH_URL" >&2
      exit 1
      ;;
  esac
  if command -v sha256sum >/dev/null 2>&1; then
    health_sha256="$(sha256sum "$body_file" | awk '{print $1}')"
  else
    health_sha256="$(python3 - "$body_file" <<'PY'
import hashlib
import pathlib
import sys

print(hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest())
PY
)"
  fi
fi

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

$PYTHON_BIN - "$LEDGER_PATH" "$PRIMARY_TIP" "$SECONDARY_TIP" "$SECONDARY_ID" "$SECONDARY_PROVIDER" "$SECONDARY_HEALTH_URL" "$health_status_code" "$health_sha256" "$DEPLOYMENT_EVIDENCE" "$REPLAYED_ROWS" <<'PY'
import hashlib
import json
import pathlib
import sys
import time

path = pathlib.Path(sys.argv[1])
primary_tip = sys.argv[2]
secondary_tip = sys.argv[3]
secondary_id = sys.argv[4]
secondary_provider = sys.argv[5]
secondary_health_url = sys.argv[6]
secondary_health_status_code = sys.argv[7]
secondary_health_sha256 = sys.argv[8]
deployment_evidence = sys.argv[9]
replayed_rows = int(sys.argv[10])
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
    "replayed_rows": replayed_rows,
    "tip_parity": primary_tip == secondary_tip,
}
if secondary_provider:
    row["secondary_provider"] = secondary_provider
if secondary_health_url:
    row["secondary_health_url"] = secondary_health_url
if secondary_health_status_code:
    row["secondary_health_status_code"] = int(secondary_health_status_code)
if secondary_health_sha256:
    row["secondary_health_sha256"] = secondary_health_sha256
if deployment_evidence:
    row["deployment_evidence"] = deployment_evidence
body = {k: v for k, v in row.items() if k != "this_hash"}
row["this_hash"] = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
with path.open("a", encoding="utf-8", newline="\n") as handle:
    handle.write(json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n")
print(f"substrate-portability: wrote dry-run row seq={row['seq']} tip_parity={row['tip_parity']}")
PY
