#!/usr/bin/env bash
# Operator helper: set XION_AKASH_HTTPS_BASE and source chutes.env, then closeout.
# Usage: bash scripts/run-closeout-with-lease.sh https://host:port
# Each run appends a new `SUBSTRATE_DRYRUN_LEDGER` row and bumps `as_of_utc_ns`;
# re-execute only when you intend a fresh dry-run (not for pure registry hash refresh).
set -euo pipefail
export XION_AKASH_HTTPS_BASE="${1:?usage: $0 https://lease-host:port}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
SECRETS="${XION_CHUTES_SECRETS_FILE:-/mnt/c/Users/16823/Documents/xion/xion-secrets/chutes.env}"
if [[ -f "$SECRETS" ]]; then
  set -a
  # shellcheck disable=SC1090
  source <(sed 's/\r$//' "$SECRETS")
  set +a
fi
cd "$REPO"
exec bash scripts/closeout-genesis-akash-primary-wsl.sh
