#!/usr/bin/env bash
# Publish ledgers/RELAY_REGISTRY.json to Arweave (WSL). Requires a funded JWK
# (default: $HOME/.aos.json) and a local venv with arweave-python-client.
# Usage: export XION_REGISTRY_WALLET_JWK_PATH=/path/to/key.json  # optional
#        bash scripts/publish-relay-registry-wsl.sh
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
exec "$PY" "${REPO}/scripts/publish-relay-registry-arweave.py"
