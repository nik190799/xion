#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${XION_REPO_URL:-https://github.com/nik190799/xion.git}"
REPO_REF="${XION_REPO_REF:-main}"
WORKDIR="$(mktemp -d 2>/dev/null || mktemp -d -t xion-third-party-drill)"
RESULTS_JSONL="$WORKDIR/results.jsonl"
HEALTH_JSONL="$WORKDIR/health.jsonl"

cleanup() {
  rm -rf "$WORKDIR"
}
trap cleanup EXIT

if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="${PYTHON:-python3}"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="${PYTHON:-python}"
else
  echo "immortality-drill-third-party: no python interpreter found" >&2
  exit 127
fi

for required in git curl; do
  if ! command -v "$required" >/dev/null 2>&1; then
    echo "immortality-drill-third-party: missing required command: $required" >&2
    exit 127
  fi
done

git clone --quiet "$REPO_URL" "$WORKDIR/repo"
git -C "$WORKDIR/repo" checkout --quiet "$REPO_REF"

"$PYTHON_BIN" -m venv "$WORKDIR/venv"
# shellcheck disable=SC1091
source "$WORKDIR/venv/bin/activate"
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -e "$WORKDIR/repo" -e "$WORKDIR/repo/xion-verify"

cd "$WORKDIR/repo"
COMMIT_SHA="$(git rev-parse HEAD)"

run_check() {
  local name="$1"
  shift
  local output_file="$WORKDIR/${name//[^A-Za-z0-9_.-]/_}.out"
  set +e
  "$@" >"$output_file" 2>&1
  local exit_code=$?
  set -e
  python - "$name" "$exit_code" "$output_file" >>"$RESULTS_JSONL" <<'PY'
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

name = sys.argv[1]
exit_code = int(sys.argv[2])
output = Path(sys.argv[3]).read_bytes()
print(
    json.dumps(
        {
            "name": name,
            "exit_code": exit_code,
            "output_sha256": hashlib.sha256(output).hexdigest(),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
)
PY
}

run_check "xion-verify discovery" xion-verify discovery
run_check "xion-verify gateway-conformance" xion-verify gateway-conformance
run_check "xion-verify links" xion-verify links
run_check "xion-verify schemas" xion-verify schemas
run_check "xion-verify substrate-portability" xion-verify substrate-portability
run_check "xion-verify inference-sovereignty" xion-verify inference-sovereignty
run_check "xion-verify --self-test" xion-verify --self-test

read -r AKASH_HEALTH_URL CHUTES_HEALTH_URL < <(
  python - <<'PY'
from __future__ import annotations

import json
from pathlib import Path

registry = json.loads(Path("ledgers/RELAY_REGISTRY.json").read_text(encoding="utf-8"))
relays = registry["relays"]
print(f"{relays[0]['endpoint'].rstrip('/')}/health {relays[1]['endpoint'].rstrip('/')}/health")
PY
)
AKASH_HEALTH_URL="${XION_AKASH_HEALTH_URL:-$AKASH_HEALTH_URL}"
CHUTES_HEALTH_URL="${XION_CHUTES_HEALTH_URL:-$CHUTES_HEALTH_URL}"

probe_health() {
  local name="$1"
  local url="$2"
  local body_file="$WORKDIR/${name}.body"
  set +e
  local auth_header=""
  if [[ "$name" == *"chutes"* && -n "${XION_SECONDARY_HEALTH_BEARER:-}" ]]; then
    auth_header="Authorization: Bearer $XION_SECONDARY_HEALTH_BEARER"
  fi

  if [[ -n "$auth_header" ]]; then
    status_code="$(curl --location --silent --show-error --insecure --max-time 20 --header "$auth_header" --output "$body_file" --write-out "%{http_code}" "$url")"
  else
    status_code="$(curl --location --silent --show-error --insecure --max-time 20 --output "$body_file" --write-out "%{http_code}" "$url")"
  fi
  local curl_exit=$?
  set -e
  python - "$name" "$url" "$status_code" "$curl_exit" "$body_file" >>"$HEALTH_JSONL" <<'PY'
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

name = sys.argv[1]
url = sys.argv[2]
status_code = int(sys.argv[3]) if sys.argv[3].isdigit() else 0
curl_exit = int(sys.argv[4])
body = Path(sys.argv[5]).read_bytes() if Path(sys.argv[5]).is_file() else b""
print(
    json.dumps(
        {
            "name": name,
            "url": url,
            "curl_exit": curl_exit,
            "status_code": status_code,
            "body_sha256": hashlib.sha256(body).hexdigest(),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
)
PY
}

probe_health "akash-primary-health" "$AKASH_HEALTH_URL"
probe_health "chutes-secondary-health" "$CHUTES_HEALTH_URL"

python - "$COMMIT_SHA" "$RESULTS_JSONL" "$HEALTH_JSONL" <<'PY'
from __future__ import annotations

import hashlib
import json
import platform
import socket
import sys
import time
import uuid
from pathlib import Path

commit_sha = sys.argv[1]
results = [json.loads(line) for line in Path(sys.argv[2]).read_text(encoding="utf-8").splitlines() if line.strip()]
health = [json.loads(line) for line in Path(sys.argv[3]).read_text(encoding="utf-8").splitlines() if line.strip()]
ledger = Path("ledgers/IMMORTALITY_DRILL_LEDGER.jsonl")
prev_hash = ""
if ledger.is_file():
    rows = [line for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()]
    if rows:
        prev_hash = json.loads(rows[-1]).get("row_hash", "")

all_verifiers_ok = all(int(row["exit_code"]) == 0 for row in results)
all_health_ok = all(int(row["curl_exit"]) == 0 and 200 <= int(row["status_code"]) <= 299 for row in health)
machine_fingerprint = hashlib.sha256(
    f"{platform.platform()}|{socket.gethostname()}|{platform.python_version()}".encode("utf-8")
).hexdigest()
row = {
    "schema_version": 1,
    "event": "immortality_drill_third_party_v1",
    "run_id": str(uuid.uuid4()),
    "as_of_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "primary_substrate": "akash-public-primary",
    "secondary_substrate": "chutes-public-secondary",
    "status": "passed" if all_verifiers_ok and all_health_ok else "failed",
    "residual_closed": False,
    "residual": "LHT-SUBSTRATE-001",
    "third_party_machine_fingerprint": machine_fingerprint,
    "repo_commit_sha": commit_sha,
    "verifier_results": results,
    "relay_health_results": health,
    "prev_hash": prev_hash,
}
payload = json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
row["row_hash"] = hashlib.sha256(payload).hexdigest()
print(json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
PY
