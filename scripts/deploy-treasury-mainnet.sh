#!/usr/bin/env bash
# Compatibility wrapper: Base treasury deploy now lives in xion_ops.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"
exec python -m xion_ops base-evm deploy-treasury --network base "$@"
