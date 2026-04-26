#!/usr/bin/env bash
# Debug helper for Chutes D3 Relay deployment.
# Reads chutes.env (CHUTES_API_KEY, CHUTES_API_URL) and exercises the public
# /health endpoint plus the chutes CLI status surface so we can see whether the
# instance is alive at the moment of the probe.

set -euo pipefail

SECRETS_FILE="${CHUTES_ENV_FILE:-/mnt/c/Users/16823/Documents/xion/xion-secrets/chutes.env}"
CHUTE_NAME="${CHUTE_NAME:-xion-relay-pre-genesis-d3}"
PUBLIC_URL="${CHUTE_PUBLIC_URL:-https://nikhilkadalge-xion-relay-pre-genesis-d3.chutes.ai}"

if [[ ! -f "$SECRETS_FILE" ]]; then
  echo "missing chutes secrets file: $SECRETS_FILE" >&2
  exit 1
fi

# shellcheck disable=SC1090
source "$SECRETS_FILE"

if [[ -z "${CHUTES_API_KEY:-}" ]]; then
  echo "CHUTES_API_KEY not set after sourcing $SECRETS_FILE" >&2
  exit 1
fi

echo "=== chutes chutes get $CHUTE_NAME (instances + version slice) ==="
chutes chutes get "$CHUTE_NAME" 2>/dev/null \
  | python3 -c '
import json, sys
raw = sys.stdin.read()
start = raw.find("{")
if start < 0:
    print(raw)
    sys.exit(0)
data = json.loads(raw[start:])
print("chute_id      :", data.get("chute_id"))
print("version       :", data.get("version"))
print("updated_at    :", data.get("updated_at"))
print("max_instances :", data.get("max_instances"))
print("shutdown_after:", str(data.get("shutdown_after_seconds")) + "s")
print("hot           :", data.get("hot"))
print("instances     :")
for inst in data.get("instances", []) or []:
    print(
        "  - id=" + str(inst.get("instance_id")),
        "active=" + str(inst.get("active")),
        "verified=" + str(inst.get("verified")),
        "last_verified_at=" + str(inst.get("last_verified_at")),
    )
'

echo
echo "=== GET $PUBLIC_URL/health ==="
curl -sS -o /tmp/xion-chute-health.json -w "http_code=%{http_code} time_total=%{time_total}s\n" \
  -H "Authorization: Bearer $CHUTES_API_KEY" \
  "$PUBLIC_URL/health" || true
echo "--- body ---"
cat /tmp/xion-chute-health.json || true
echo

echo "=== POST $PUBLIC_URL/health (Chutes invocation form) ==="
curl -sS -o /tmp/xion-chute-health-post.json -w "http_code=%{http_code} time_total=%{time_total}s\n" \
  -X POST \
  -H "Authorization: Bearer $CHUTES_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{}' \
  "$PUBLIC_URL/health" || true
echo "--- body ---"
cat /tmp/xion-chute-health-post.json || true
echo
