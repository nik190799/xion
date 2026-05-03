#!/usr/bin/env bash
# Compatibility wrapper: Chutes cords verification now lives in xion_ops.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"
exec python -m xion_ops chutes verify-cords "$@"
