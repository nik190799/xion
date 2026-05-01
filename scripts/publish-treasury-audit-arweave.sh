#!/usr/bin/env bash
# Publish the 2026 treasury audit report and Invariant 18 ratification row to Arweave.
# Usage:
#   export XION_REGISTRY_WALLET_JWK_PATH=/path/to/funded-jwk.json  # optional, defaults to $HOME/.aos.json
#   bash scripts/publish-treasury-audit-arweave.sh
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"
export XION_REGISTRY_WALLET_JWK_PATH="${XION_REGISTRY_WALLET_JWK_PATH:-$HOME/.aos.json}"
VENV="${REPO}/.venv-arweave"
PY="${VENV}/bin/python"
if [[ ! -x "$PY" ]]; then
  python3 -m venv "$VENV"
  "$VENV"/bin/pip install -q arweave-python-client
fi
exec "$PY" "${REPO}/scripts/publish-treasury-audit-arweave.py"
