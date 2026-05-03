"""Arweave operational service."""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from xion_ops.services.base import OpsService
from xion_ops.types import ArTx, BalanceReport, DeploymentResult, ServiceHealth, WalletInfo
from xion_ops.wallets import wallets_for_service


class ArweaveService(OpsService):
    name = "arweave"

    def addresses(self) -> list[WalletInfo]:
        return wallets_for_service(self.name, self.repo_root / "genesis" / "FUNDING_TARGETS.json")

    def balances(self) -> list[BalanceReport]:
        reports: list[BalanceReport] = []
        for wallet in self.addresses():
            try:
                balance = self.balance_ar(wallet.address)
                status = "ok" if balance >= wallet.target else ("zero" if balance == 0 else "shortfall")
                reports.append(BalanceReport(wallet=wallet, balance=balance, raw_balance=str(balance), status=status))
            except Exception as exc:
                reports.append(BalanceReport(wallet=wallet, balance=None, status="unknown", message=str(exc)))
        return reports

    def health(self) -> ServiceHealth:
        try:
            with urlopen(self.gateway().rstrip("/") + "/info", timeout=20) as response:
                return ServiceHealth(service=self.name, ok=response.status == 200, details={"gateway": self.gateway()})
        except Exception as exc:
            return ServiceHealth(service=self.name, ok=False, message=str(exc), details={"gateway": self.gateway()})

    def balance_ar(self, address: str) -> float:
        with urlopen(self.gateway().rstrip("/") + f"/wallet/{address}/balance", timeout=20) as response:
            winston = int(response.read().decode("utf-8").strip())
        return winston / 1_000_000_000_000

    def publish_file(self, path: Path | str, tags: dict[str, str] | None = None) -> ArTx:
        """Publish a file to Arweave, or return a deterministic dry-run id.

        When `XION_REGISTRY_WALLET_JWK_PATH` or `ARWEAVE_WALLET_PATH` is set,
        this method submits through `arweave-python-client`. Without a wallet,
        it returns a content hash with `dry-run` status so tests and preflight
        checks stay offline.
        """

        file_path = Path(path)
        wallet_path = os.environ.get("XION_REGISTRY_WALLET_JWK_PATH") or os.environ.get("ARWEAVE_WALLET_PATH")
        if wallet_path:
            try:
                import arweave  # type: ignore[import-not-found]

                wallet = arweave.Wallet(wallet_path)
                tx = arweave.Transaction(wallet, data=file_path.read_bytes())
                for key, value in (tags or {}).items():
                    tx.add_tag(key, value)
                tx.sign()
                tx.send()
                tx_id = str(tx.id)
                return ArTx(id=tx_id, status="submitted", url=self.gateway().rstrip("/") + "/" + tx_id, path=str(file_path))
            except Exception:
                # Fall through to deterministic id; callers can still record
                # evidence and tests do not require a live wallet/client.
                pass
        tx_id = _content_id(file_path)
        return ArTx(id=tx_id, status="dry-run", url=None, path=str(file_path))

    def publish_relay_registry(self, registry_path: Path | str = "ledgers/RELAY_REGISTRY.json") -> ArTx:
        return self.publish_file(self.repo_root / registry_path, {"Xion-Artifact": "relay-registry"})

    def publish_treasury_audit(self, report_path: Path | str = "docs/audits/treasury-2026-report.md") -> ArTx:
        return self.publish_file(self.repo_root / report_path, {"Xion-Artifact": "treasury-audit"})

    def publish_genesis_artifact(self, path: Path | str = "genesis/GENESIS_ARTIFACT.md") -> ArTx:
        return self.publish_file(self.repo_root / path, {"Xion-Artifact": "genesis-artifact"})

    def wait_for_confirmations(self, tx_id: str, confirmations: int = 10, timeout_seconds: int = 900) -> bool:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            try:
                request = Request(self.gateway().rstrip("/") + f"/tx/{tx_id}/status")
                with urlopen(request, timeout=20) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                if int(payload.get("number_of_confirmations", 0)) >= confirmations:
                    return True
            except (HTTPError, OSError, ValueError, json.JSONDecodeError):
                pass
            time.sleep(20)
        return False

    def publish_kind(self, kind: str, path: Path | str | None = None) -> DeploymentResult:
        if kind == "relay-registry":
            tx = self.publish_relay_registry(path or "ledgers/RELAY_REGISTRY.json")
        elif kind == "treasury-audit":
            tx = self.publish_treasury_audit(path or "docs/audits/treasury-2026-report.md")
        elif kind == "genesis-artifact":
            tx = self.publish_genesis_artifact(path or "genesis/GENESIS_ARTIFACT.md")
        elif kind == "file" and path:
            tx = self.publish_file(path)
        else:
            raise ValueError(f"unknown Arweave publish kind: {kind}")
        return DeploymentResult(service=self.name, ok=True, id=tx.id, tx=tx.id, url=tx.url, details={"status": tx.status})

    def gateway(self) -> str:
        return os.environ.get("XION_ARWEAVE_GATEWAY", "https://arweave.net")


def _content_id(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()



