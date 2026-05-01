#!/usr/bin/env bash
# Register/deploy the Base mainnet Vault through MasterTreasury.
#
# Required env:
#   BASE_MAINNET_RPC
#   XION_DEPLOYER_PRIVATE_KEY
#   XION_MAINNET_MASTER_TREASURY
#   XION_AO_CORE_AUTHORITY
# Optional env:
#   XION_VAULT_CHAIN_ID=8453
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"

: "${BASE_MAINNET_RPC:?set BASE_MAINNET_RPC}"
: "${XION_DEPLOYER_PRIVATE_KEY:?set XION_DEPLOYER_PRIVATE_KEY}"
: "${XION_MAINNET_MASTER_TREASURY:?set XION_MAINNET_MASTER_TREASURY}"
: "${XION_AO_CORE_AUTHORITY:?set XION_AO_CORE_AUTHORITY}"
CHAIN_ID="${XION_VAULT_CHAIN_ID:-8453}"

if ! command -v cast >/dev/null 2>&1; then
  echo "deploy-vault-mainnet: cast executable not found" >&2
  exit 2
fi

TMP_RECEIPT="$(mktemp)"
cast send \
  "$XION_MAINNET_MASTER_TREASURY" \
  "deployVault(uint256,address)(address)" \
  "$CHAIN_ID" \
  "$XION_AO_CORE_AUTHORITY" \
  --rpc-url "$BASE_MAINNET_RPC" \
  --private-key "$XION_DEPLOYER_PRIVATE_KEY" \
  --json > "$TMP_RECEIPT"

VAULT_ADDRESS="$(cast call "$XION_MAINNET_MASTER_TREASURY" "vaultForChain(uint256)(address)" "$CHAIN_ID" --rpc-url "$BASE_MAINNET_RPC")"

python - "$TMP_RECEIPT" "$VAULT_ADDRESS" "$CHAIN_ID" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

receipt_path = Path(sys.argv[1])
vault_address = sys.argv[2].strip()
chain_id = int(sys.argv[3])
receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
root = Path.cwd()

deploy_receipt = root / "genesis" / "treasury_mainnet_deploy_receipt.json"
data = {}
if deploy_receipt.is_file():
    data = json.loads(deploy_receipt.read_text(encoding="utf-8"))

data["vault"] = {
    "network": "base",
    "chain_id": chain_id,
    "vault": vault_address,
    "deploy_tx": receipt.get("transactionHash"),
    "deploy_block": receipt.get("blockNumber"),
}

deploy_receipt.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(f"deploy-vault-mainnet: wrote {deploy_receipt}")
print(f"deploy-vault-mainnet: Vault {vault_address}")
PY

rm -f "$TMP_RECEIPT"
