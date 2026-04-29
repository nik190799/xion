#!/usr/bin/env bash
# Probe every public cord on the Xion Relay chute. In smoke mode, assert the
# deterministic d3-6 smoke envelope. In live mode, assert the proxied FastAPI
# Relay response shapes.

set -euo pipefail

SECRETS_FILE="${CHUTES_ENV_FILE:-/mnt/c/Users/16823/Documents/xion/xion-secrets/chutes.env}"
PUBLIC_URL="${CHUTE_PUBLIC_URL:-https://nikhilkadalge-xion-relay-pre-genesis-d3.chutes.ai}"
EXPECTED_IMAGE_TAG="${EXPECTED_IMAGE_TAG:-pre-genesis-d3-10}"
MODE="${MODE:-smoke}"

case "${1:-}" in
  --mode=smoke)
    MODE="smoke"
    shift
    ;;
  --mode=live)
    MODE="live"
    shift
    ;;
esac

if [[ "$MODE" != "smoke" && "$MODE" != "live" ]]; then
  echo "MODE must be 'smoke' or 'live' (got '$MODE')" >&2
  exit 2
fi

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
  python3 - "$body_file" "$path" "$EXPECTED_IMAGE_TAG" "$MODE" <<'PY'
import json, sys
body_path, expected_path, expected_tag, mode = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
with open(body_path) as fh:
    data = json.load(fh)
errors = []
if mode == "smoke":
    required = {"status", "service", "image_tag", "endpoint", "timestamp", "note"}
    missing = required - set(data)
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
elif expected_path == "/health":
    if "relay_healthy" not in data:
        errors.append("health missing relay_healthy")
    if "arbiter_healthy" not in data:
        errors.append("health missing arbiter_healthy")
    if "watchdog_fires_recent" not in data:
        errors.append("health missing watchdog_fires_recent")
elif expected_path == "/quote":
    if "per_message_price_micro_XION" not in data:
        errors.append("quote/pricing missing per_message_price_micro_XION")
    if "five_slice" not in data:
        errors.append("quote/pricing missing five_slice")
elif expected_path == "/self":
    required = {"topography", "sensorium", "vitals", "governance", "as_of_utc_ns"}
    missing = required - set(data)
    if missing:
        errors.append(f"self missing keys: {sorted(missing)}")
if errors:
    print("FAIL " + expected_path + ": " + "; ".join(errors))
    sys.exit(1)
print(f"OK {expected_path}: {mode} shape valid")
PY
}

for cord in /health /quote /self; do
  probe "$cord" || failed=1
done

if [[ "$failed" -ne 0 ]]; then
  echo "RESULT: at least one cord probe failed"
  exit 1
fi

echo "RESULT: all cords green"
