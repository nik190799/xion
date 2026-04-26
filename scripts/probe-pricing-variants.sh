#!/usr/bin/env bash
# Cross-check the D3 cord routing facts that are recorded in
# ``KW-RELAY-CHUTES-D3-001``:
#   1. ``GET /pricing`` is intercepted by the Chutes *platform* proxy
#      (returns the platform's GPU pricing payload).
#   2. The two-segment public path ``/xion/pricing`` returns a stable
#      nginx ``502 Bad Gateway`` (history; relevant only on d3-5).
#   3. Even with a single-segment public path ``/xpricing`` the request
#      502s if the chute function is named ``pricing`` (its internal
#      upstream path defaults to the function name and the worker-side
#      Aegis layer also intercepts ``/pricing``).  Relevant on d3-6.
# Keep this script handy when promoting the chute through new image
# tags so each fact stays empirically pinned, not folklore.
set -uo pipefail

SECRETS_FILE="${CHUTES_ENV_FILE:-/mnt/c/Users/16823/Documents/xion/xion-secrets/chutes.env}"
PUBLIC_URL="${CHUTE_PUBLIC_URL:-https://nikhilkadalge-xion-relay-pre-genesis-d3.chutes.ai}"

# shellcheck disable=SC1090
source "$SECRETS_FILE"

probe() {
  local label="$1"; local path="$2"
  echo "=== $label  GET $path ==="
  curl -sS -o /tmp/xion-cord-probe.body \
    -w 'http_code=%{http_code} time_total=%{time_total}s\n' \
    -H "Authorization: Bearer $CHUTES_API_KEY" \
    "${PUBLIC_URL}${path}" || true
  head -c 600 /tmp/xion-cord-probe.body || true
  echo
  echo
}

probe "platform-reserved /pricing       " "/pricing"
probe "stale d3-5 path  /xion/pricing  " "/xion/pricing"
probe "current cord     /xpricing      " "/xpricing"
