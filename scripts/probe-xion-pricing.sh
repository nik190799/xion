#!/usr/bin/env bash
# Retry the /xion/pricing cord a few times to distinguish a one-shot
# upstream blip (instance still warming) from a real path-routing miss.
set -uo pipefail

SECRETS_FILE="${CHUTES_ENV_FILE:-/mnt/c/Users/16823/Documents/xion/xion-secrets/chutes.env}"
PUBLIC_URL="${CHUTE_PUBLIC_URL:-https://nikhilkadalge-xion-relay-pre-genesis-d3.chutes.ai}"

# shellcheck disable=SC1090
source "$SECRETS_FILE"

for i in 1 2 3 4 5; do
  echo "--- attempt $i ---"
  curl -sS -o /tmp/xion-cord-pricing.json \
    -w 'http_code=%{http_code} time_total=%{time_total}s\n' \
    -H "Authorization: Bearer $CHUTES_API_KEY" \
    "${PUBLIC_URL}/xpricing" || true
  cat /tmp/xion-cord-pricing.json || true
  echo
  sleep 5
done
