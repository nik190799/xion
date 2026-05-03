#!/usr/bin/env bash
# Compatibility wrapper: Chutes cords verification now lives in xion_ops.
# Exits non-zero when any of /health /quote /self is not 2xx (unless you pass
# --allow-failure through to the CLI, e.g. for JSON-only scrapers).
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"
exec python -m xion_ops chutes verify-cords "$@"
