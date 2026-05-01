#!/usr/bin/env bash
# Deploy MasterTreasury to Base mainnet and write a structured receipt.
#
# Required env:
#   BASE_MAINNET_RPC
#   XION_DEPLOYER_PRIVATE_KEY
#   XION_TREASURY_GOVERNANCE
#   XION_AO_CORE_AUTHORITY
# Optional env:
#   XION_BRIDGE_CAP_BPS=1000
#   BASESCAN_API_KEY
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"

: "${BASE_MAINNET_RPC:?set BASE_MAINNET_RPC}"
: "${XION_DEPLOYER_PRIVATE_KEY:?set XION_DEPLOYER_PRIVATE_KEY}"
: "${XION_TREASURY_GOVERNANCE:?set XION_TREASURY_GOVERNANCE}"
: "${XION_AO_CORE_AUTHORITY:?set XION_AO_CORE_AUTHORITY}"
export XION_BRIDGE_CAP_BPS="${XION_BRIDGE_CAP_BPS:-1000}"

if ! command -v forge >/dev/null 2>&1; then
  echo "deploy-treasury-mainnet: forge executable not found" >&2
  exit 2
fi

CMD=(
  forge script contracts/treasury/script/Deploy.s.sol:DeployTreasury
  --rpc-url "$BASE_MAINNET_RPC"
  --broadcast
  --private-key "$XION_DEPLOYER_PRIVATE_KEY"
)

if [[ -n "${BASESCAN_API_KEY:-}" ]]; then
  CMD+=(--verify --etherscan-api-key "$BASESCAN_API_KEY")
fi

"${CMD[@]}"

python - <<'PY'
from __future__ import annotations

import json
from pathlib import Path

root = Path.cwd()
broadcast_dir = root / "broadcast" / "Deploy.s.sol" / "8453"
latest = broadcast_dir / "run-latest.json"
if not latest.is_file():
    raise SystemExit(f"deploy-treasury-mainnet: missing {latest}")

data = json.loads(latest.read_text(encoding="utf-8"))
transactions = data.get("transactions") or []
master = None
for tx in transactions:
    if tx.get("contractName") == "MasterTreasury" and tx.get("contractAddress"):
        master = tx
        break
if master is None:
    raise SystemExit("deploy-treasury-mainnet: no MasterTreasury deployment found in run-latest.json")

receipt = {
    "schema_version": 1,
    "network": "base",
    "chain_id": 8453,
    "artifact": "MasterTreasury",
    "contract_address": master.get("contractAddress"),
    "deploy_tx": master.get("hash") or master.get("transactionHash"),
    "deploy_block": master.get("blockNumber"),
    "broadcast_file": str(latest.relative_to(root)).replace("\\", "/"),
    "governance": master.get("arguments", [None, None, None])[0],
    "bridge_exposure_cap_bps": master.get("arguments", [None, None, None])[1],
    "ao_core_authority": master.get("arguments", [None, None, None])[2],
}

out = root / "genesis" / "treasury_mainnet_deploy_receipt.json"
out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(f"deploy-treasury-mainnet: wrote {out}")
print(f"deploy-treasury-mainnet: MasterTreasury {receipt['contract_address']}")
PY
