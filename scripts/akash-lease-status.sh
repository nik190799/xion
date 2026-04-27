#!/usr/bin/env bash
# Print `lease-status` JSON (mTLS) for a known deployment. Default dseq/provider
# match the runbook’s mainnet example; override for other leases.
# Usage: bash scripts/akash-lease-status.sh [dseq] [provider] [key_name]
set -euo pipefail
export PATH="${HOME}/bin:${PATH:-}"
export AKASH_CHAIN_ID="${AKASH_CHAIN_ID:-akashnet-2}"
export AKASH_NODE="${AKASH_NODE:-https://rpc.akashnet.net:443}"
DSEQ="${1:-26563373}"
PROVIDER="${2:-akash1x2g8wfa429fukudgkclaag00d00z4rn846j7wq}"
KEY="${3:-xion-b5}"

provider-services lease-status --dseq "$DSEQ" --provider "$PROVIDER" \
  --from "$KEY" --keyring-backend test --node "$AKASH_NODE" --auth-type mtls
