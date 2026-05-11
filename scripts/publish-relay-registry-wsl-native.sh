#!/usr/bin/env bash
# Run Arweave registry publish from WSL with the native ~/.aos.json wallet.
# Bypasses the xion_ops Windows-side check that mis-handles a WSL-format
# XION_REGISTRY_WALLET_JWK_PATH when invoked from PowerShell. Submits the
# transaction via arweave-python-client and prints the resulting tx id.
set -eu
cd "$(dirname "$0")/.."
unset XION_REGISTRY_WALLET_JWK_PATH ARWEAVE_WALLET_PATH || true
if [ ! -f "$HOME/.aos.json" ]; then
  echo "NO_JWK at $HOME/.aos.json" >&2
  exit 44
fi
PY=python3
if [ -x .venv-arweave/bin/python ]; then PY=.venv-arweave/bin/python; fi
XION_REGISTRY_WALLET_JWK_PATH="$HOME/.aos.json" "$PY" - <<'PY'
import json
from xion_ops.services.arweave import ArweaveService
tx = ArweaveService(repo_root=".").publish_relay_registry("ledgers/RELAY_REGISTRY.json")
print(json.dumps(tx.__dict__, sort_keys=True))
PY
