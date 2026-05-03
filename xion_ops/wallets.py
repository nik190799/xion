"""Funding-target registry loader."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from xion_ops.exceptions import ConfigError
from xion_ops.types import SecondaryTarget, WalletInfo

DEFAULT_FUNDING_TARGETS = Path("genesis/FUNDING_TARGETS.json")


def load_funding_targets(path: Path | str = DEFAULT_FUNDING_TARGETS) -> list[WalletInfo]:
    registry_path = Path(path)
    if not registry_path.exists():
        raise ConfigError(f"funding-target registry missing: {registry_path}")
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise ConfigError("FUNDING_TARGETS schema_version must be 1")
    wallets = payload.get("wallets")
    if not isinstance(wallets, list):
        raise ConfigError("FUNDING_TARGETS wallets must be a list")
    return [_parse_wallet(row, idx) for idx, row in enumerate(wallets)]


def wallets_for_service(service: str, path: Path | str = DEFAULT_FUNDING_TARGETS) -> list[WalletInfo]:
    return [wallet for wallet in load_funding_targets(path) if wallet.service == service]


def _parse_wallet(row: Any, idx: int) -> WalletInfo:
    if not isinstance(row, dict):
        raise ConfigError(f"wallet[{idx}] must be an object")
    required = ("id", "address", "network", "currency", "target", "purpose", "service")
    missing = [key for key in required if key not in row]
    if missing:
        raise ConfigError(f"wallet[{idx}] missing required key(s): {', '.join(missing)}")
    secondary = tuple(
        SecondaryTarget(currency=str(item["currency"]), target=float(item["target"]))
        for item in row.get("secondary", [])
    )
    return WalletInfo(
        id=str(row["id"]),
        address=str(row["address"]),
        network=str(row["network"]),
        currency=str(row["currency"]),
        target=float(row["target"]),
        purpose=str(row["purpose"]),
        service=str(row["service"]),
        secondary=secondary,
    )

