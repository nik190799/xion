#!/usr/bin/env python3
"""Print Arweave address and balance for XION_REGISTRY_WALLET_JWK_PATH or ~/.aos.json."""
import os

import arweave

path = os.environ.get("XION_REGISTRY_WALLET_JWK_PATH") or os.path.expanduser("~/.aos.json")
w = arweave.Wallet(path)
raw = float(w.balance)
print("path:", path)
print("address:", w.address)
print("balance_AR:", raw)
