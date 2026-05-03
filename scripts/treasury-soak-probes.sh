#!/usr/bin/env bash
# Cast-call probes for MasterTreasury (Base Sepolia rehearsal or Base mainnet).
# RPC follows genesis/TREASURY_VAULTS.json status (see treasury_soak_probes.py).
# Usage: from repo root, with forge on PATH (or WSL — prefer verify-mainnet-deploy-gates host).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

if [[ -f "${ROOT}/.env" ]]; then
  set -a && source "${ROOT}/.env" && set +a
fi

if command -v python3 >/dev/null 2>&1; then PY=python3; else PY=python; fi
RPC="$("${PY}" -c "import json, os; m=json.load(open('genesis/TREASURY_VAULTS.json')); s=m.get('status','testnet'); print((os.environ.get('BASE_MAINNET_RPC') or os.environ.get('XION_BASE_MAINNET_RPC') or 'https://mainnet.base.org') if s=='mainnet' else (os.environ.get('BASE_SEPOLIA_RPC') or os.environ.get('XION_BASE_SEPOLIA_RPC') or 'https://sepolia.base.org'))")"
MASTER="$("${PY}" -c 'import json; print(json.load(open("genesis/TREASURY_VAULTS.json"))["master_treasury"])')"

echo "[treasury-soak-probes] rpc=${RPC}"
echo "[treasury-soak-probes] master_treasury=${MASTER}"

if ! command -v cast >/dev/null 2>&1; then
  echo "[treasury-soak-probes] SKIP: foundry cast not on PATH"
  exit 0
fi

_cast() {
  if command -v timeout >/dev/null 2>&1; then
    timeout 120 cast "$@"
  else
    cast "$@"
  fi
}

_cast call "${MASTER}" "governance()(address)" --rpc-url "${RPC}"
_cast call "${MASTER}" "aoCoreAuthority()(address)" --rpc-url "${RPC}"
_cast call "${MASTER}" "registeredChainCount()(uint256)" --rpc-url "${RPC}"

echo "[treasury-soak-probes] OK"
