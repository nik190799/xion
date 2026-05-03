#!/usr/bin/env bash
# Compatibility wrapper: Arweave Relay registry publish now lives in xion_ops.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"
exec python -m xion_ops arweave publish-relay-registry "$@"
