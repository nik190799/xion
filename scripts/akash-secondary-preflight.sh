#!/usr/bin/env bash
# Compatibility wrapper: Akash preflight now lives in xion_ops.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"
exec python -m xion_ops akash preflight "$@"
