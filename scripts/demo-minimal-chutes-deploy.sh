#!/usr/bin/env bash
# Demo: Chutes CLI auth smoke and optional full build+deploy for xion_relay_chute:chute.
#
# Official docs (read first):
#   https://chutes.ai/docs/getting-started/quickstart
#   https://chutes.ai/docs/cli/overview
#   https://chutes.ai/docs/cli/build
#   https://chutes.ai/docs/cli/deploy
#   https://chutes.ai/docs/guides/custom-chutes
#
# Xion runbook:
#   docs/runbooks/CHUTES_RELAY_DEPLOY.md
#
# Env:
#   XION_CHUTES_API_KEY or CHUTES_API_KEY (required for images-list and deploy).
#
# Default: cheap path — images-list only (no image-history quota).
# Full vendor flow: set DEMO_CHUTES_FULL_DEPLOY=1 to run:
#   chutes build xion_relay_chute:chute --wait
#   chutes deploy xion_relay_chute:chute --accept-fee
#   (consumes quota / may incur fees per Chutes docs.)
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

echo "demo-minimal-chutes-deploy: repo root=$REPO_ROOT"
echo "  Official: https://chutes.ai/docs/cli/overview"
echo "  Runbook:  docs/runbooks/CHUTES_RELAY_DEPLOY.md"
echo ""

if [[ -z "${XION_CHUTES_API_KEY:-}" && -z "${CHUTES_API_KEY:-}" ]]; then
  echo "demo-minimal-chutes-deploy: set XION_CHUTES_API_KEY or CHUTES_API_KEY" >&2
  exit 2
fi

echo "demo-minimal-chutes-deploy: chutes images-list (API smoke)..."
python -m xion_ops chutes images-list --limit 5

if [[ "${DEMO_CHUTES_FULL_DEPLOY:-}" == "1" ]]; then
  echo "demo-minimal-chutes-deploy: DEMO_CHUTES_FULL_DEPLOY=1 — chutes build --wait..."
  chutes build xion_relay_chute:chute --wait
  echo "demo-minimal-chutes-deploy: chutes deploy --accept-fee..."
  chutes deploy xion_relay_chute:chute --accept-fee
  echo "demo-minimal-chutes-deploy: optional cord check (non-fatal)..."
  python -m xion_ops chutes verify-cords --allow-failure || true
else
  echo "demo-minimal-chutes-deploy: skip build/deploy (set DEMO_CHUTES_FULL_DEPLOY=1 to run chutes build+deploy)."
fi

echo "demo-minimal-chutes-deploy: OK"
