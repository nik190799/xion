#!/usr/bin/env bash
# Probe every public cord on the Xion Relay smoke chute and assert each one
# returns the deterministic envelope shape we declare in
# ``xion_relay_chute._smoke_envelope``.

set -euo pipefail

SECRETS_FILE="${CHUTES_ENV_FILE:-/mnt/c/Users/16823/Documents/xion/xion-secrets/chutes.env}"
PUBLIC_URL="${CHUTE_PUBLIC_URL:-https://nikhilkadalge-xion-relay-pre-genesis-d3.chutes.ai}"
EXPECTED_IMAGE_TAG="${EXPECTED_IMAGE_TAG:-pre-genesis-d3-7}"

# shellcheck disable=SC1090
source "$SECRETS_FILE"

failed=0

probe() {
  local path="$1"
  local body_file="/tmp/xion-cord-${path//\//_}.json"
  local http_code
  http_code=$(curl -sS -o "$body_file" -w "%{http_code}" \
    -H "Authorization: Bearer $CHUTES_API_KEY" \
    "${PUBLIC_URL}${path}" || echo "curl_failed")
  echo "=== GET $path -> $http_code ==="
  cat "$body_file"
  echo
  if [[ "$http_code" != "200" ]]; then
    echo "FAIL $path: expected 200, got $http_code" >&2
    failed=1
    return
  fi
  python3 - "$body_file" "$path" "$EXPECTED_IMAGE_TAG" <<'PY'
import json, sys
body_path, expected_path, expected_tag = sys.argv[1], sys.argv[2], sys.argv[3]
with open(body_path) as fh:
    data = json.load(fh)
required = {"status", "service", "image_tag", "endpoint", "timestamp", "note"}
missing = required - set(data)
errors = []
if missing:
    errors.append(f"missing keys: {sorted(missing)}")
if data.get("status") != "ok":
    errors.append(f"status != 'ok' (got {data.get('status')!r})")
if data.get("service") != "xion-relay-chutes-smoke":
    errors.append(f"service != 'xion-relay-chutes-smoke' (got {data.get('service')!r})")
if data.get("image_tag") != expected_tag:
    errors.append(f"image_tag != {expected_tag!r} (got {data.get('image_tag')!r})")
if data.get("endpoint") != expected_path:
    errors.append(f"endpoint != {expected_path!r} (got {data.get('endpoint')!r})")
if errors:
    print("FAIL " + expected_path + ": " + "; ".join(errors))
    sys.exit(1)
print(f"OK {expected_path}: envelope shape valid")
PY
}

for cord in /health /xpricing /self; do
  probe "$cord" || failed=1
done

if [[ "$failed" -ne 0 ]]; then
  echo "RESULT: at least one cord probe failed"
  exit 1
fi

echo "RESULT: all cords green"
