#!/usr/bin/env bash
# Preflight for B5: warm non-laptop secondary substrate (Akash path).
#
# This script is intentionally read-only. It does not create leases, spend AKT,
# or append the dry-run ledger. It answers the solo-operator question:
# "Can I attempt the Akash standby deploy from this machine right now?"
set -euo pipefail

RELAY_DIGEST_FILE="${XION_RELAY_DIGEST_FILE:-genesis/RELAY_IMAGE_DIGEST.txt}"
AKASH_SDL="${XION_AKASH_SDL:-infra/akash/relay-deployment.yaml}"

failures=0

check() {
  local label="$1"
  shift
  if "$@"; then
    echo "OK   $label"
  else
    echo "MISS $label"
    failures=$((failures + 1))
  fi
}

has_command() {
  command -v "$1" >/dev/null 2>&1
}

has_akash_cli() {
  has_command akash || has_command provider-services || [[ -x "$HOME/bin/provider-services" ]]
}

check "Akash CLI (akash or provider-services)" has_akash_cli
check "Docker CLI" has_command docker
check "Relay image digest file" test -s "$RELAY_DIGEST_FILE"
check "Akash SDL" test -s "$AKASH_SDL"

if [[ -s "$RELAY_DIGEST_FILE" ]]; then
  digest="$(tr -d '[:space:]' < "$RELAY_DIGEST_FILE")"
  if [[ "$digest" =~ ^sha256:[0-9a-f]{64}$ ]]; then
    echo "OK   Relay digest format: $digest"
  else
    echo "MISS Relay digest format must be sha256:<64 hex chars> (got '$digest')"
    failures=$((failures + 1))
  fi
fi

if [[ -s "$AKASH_SDL" ]]; then
  if grep -q "pre-genesis-placeholder" "$AKASH_SDL"; then
    echo "MISS Akash SDL still uses placeholder image"
    failures=$((failures + 1))
  else
    echo "OK   Akash SDL image is non-placeholder"
  fi
fi

cat <<'EOF'

Next once preflight is green:

  1. Create an Akash lease from infra/akash/relay-deployment.yaml.
  2. Confirm the lease endpoint returns /health.
  3. Record the dry-run row with real evidence:

     XION_SECONDARY_SUBSTRATE_ID=akash-testnet-standby \
     XION_SECONDARY_PROVIDER=akash \
     XION_SECONDARY_HEALTH_URL=https://<akash-lease-host>/health \
     XION_DEPLOYMENT_EVIDENCE=akash://<owner>/<dseq>/<gseq>/<oseq> \
     XION_PRIMARY_STATE_TIP=<primary-tip> \
     XION_SECONDARY_STATE_TIP=<same-tip-after-replay> \
     bash scripts/substrate-portability-dry-run.sh

  4. Run: xion-verify substrate-portability

EOF

if [[ "$failures" -ne 0 ]]; then
  echo "B5 preflight: NOT READY ($failures missing requirement(s))"
  exit 1
fi

echo "B5 preflight: READY"
