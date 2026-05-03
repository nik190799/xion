#!/usr/bin/env bash
# Compatibility wrapper: treasury audit Arweave publish now lives in xion_ops.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"
exec python -m xion_ops arweave publish-treasury-audit "$@"
