"""Akash deployment service.

All `provider-services` invocations live here so deployers, wrappers, and HTTP
routes share one operational path.
"""

from __future__ import annotations

import json
import os
import shlex
import ssl
import time
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from xion_ops.commands import run_command
from xion_ops.exceptions import OpsError, ProviderUnreachable
from xion_ops.services.base import OpsService
from xion_ops.types import BalanceReport, CommandResult, DeploymentResult, LeaseStatus, ServiceHealth, WalletInfo
from xion_ops.wallets import wallets_for_service


class AkashService(OpsService):
    name = "akash"

    def __init__(self, *, repo_root: Path | str = ".", key: str | None = None, node: str | None = None) -> None:
        super().__init__(repo_root=repo_root)
        self.key = key or os.environ.get("XION_AKASH_KEY", "xion-b5")
        self.node = node or os.environ.get("AKASH_NODE", "https://rpc.akashnet.net:443")
        self.chain_id = os.environ.get("AKASH_CHAIN_ID", "akashnet-2")
        self.owner = os.environ.get("XION_AKASH_OWNER", self._default_owner())

    def addresses(self) -> list[WalletInfo]:
        return wallets_for_service(self.name, self.repo_root / "genesis" / "FUNDING_TARGETS.json")

    def balances(self) -> list[BalanceReport]:
        raw = self.query_bank_balances(self.owner)
        amounts = {item["denom"]: float(item["amount"]) for item in raw.get("balances", [])}
        reports: list[BalanceReport] = []
        for wallet in self.addresses():
            balance = amounts.get(wallet.currency, 0.0)
            status = "ok" if balance >= wallet.target else ("zero" if balance == 0 else "shortfall")
            reports.append(BalanceReport(wallet=wallet, balance=balance, raw_balance=str(balance), status=status))
        return reports

    def health(self) -> ServiceHealth:
        try:
            self.query_bank_balances(self.owner)
            return ServiceHealth(service=self.name, ok=True, details={"node": self.node, "owner": self.owner})
        except Exception as exc:
            return ServiceHealth(service=self.name, ok=False, message=str(exc), details={"node": self.node})

    def query_bank_balances(self, owner: str) -> dict[str, Any]:
        result = self._provider_services(
            "query",
            "bank",
            "balances",
            owner,
            "--node",
            self.node,
            "--chain-id",
            self.chain_id,
            "-o",
            "json",
        )
        return json.loads(result.stdout)

    def mint_act(self, uakt_amount: int) -> CommandResult:
        return self._provider_services(
            "tx",
            "bme",
            "mint-act",
            f"{uakt_amount}uakt",
            "--from",
            self.key,
            "--keyring-backend",
            "test",
            "--chain-id",
            self.chain_id,
            "--node",
            self.node,
            "--gas",
            "auto",
            "--gas-adjustment",
            "2",
            "--gas-prices",
            "0.5uakt",
            "-y",
            "-o",
            "json",
        )

    def wait_for_ledger_executed(self, *, timeout_seconds: int = 600, poll_seconds: int = 15) -> bool:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            ledger = self.bme_ledger()
            records = ledger.get("records", [])
            if records and all(row.get("status") == "ledger_record_status_executed" for row in records):
                return True
            time.sleep(poll_seconds)
        return False

    def bme_ledger(self) -> dict[str, Any]:
        result = self._provider_services(
            "query",
            "bme",
            "ledger",
            "--owner",
            self.owner,
            "--node",
            self.node,
            "--chain-id",
            self.chain_id,
            "-o",
            "json",
        )
        return json.loads(result.stdout)

    def create_deployment(self, sdl_path: Path | str) -> str:
        result = self._provider_services(
            "tx",
            "deployment",
            "create",
            str(sdl_path),
            "--from",
            self.key,
            "--keyring-backend",
            "test",
            "--chain-id",
            self.chain_id,
            "--node",
            self.node,
            "--gas",
            "auto",
            "--gas-adjustment",
            "2",
            "--gas-prices",
            "0.5uakt",
            "-y",
            "-o",
            "json",
        )
        payload = json.loads(result.stdout)
        for event in payload.get("events", []):
            if event.get("type") == "akash.deployment.v1.EventDeploymentCreated":
                for attr in event.get("attributes", []):
                    if attr.get("key") == "id":
                        return str(json.loads(attr["value"])["dseq"])
        raise OpsError(f"could not parse dseq from deployment create: {result.stdout}")

    def list_bids(self, dseq: str) -> list[dict[str, Any]]:
        result = self._provider_services(
            "query",
            "market",
            "bid",
            "list",
            "--owner",
            self.owner,
            "--dseq",
            str(dseq),
            "--node",
            self.node,
            "--chain-id",
            self.chain_id,
            "-o",
            "json",
        )
        return list(json.loads(result.stdout).get("bids", []))

    def accept_bid(self, dseq: str, provider: str) -> CommandResult:
        return self._provider_services(
            "tx",
            "market",
            "lease",
            "create",
            "--dseq",
            str(dseq),
            "--gseq",
            "1",
            "--oseq",
            "1",
            "--provider",
            provider,
            "--from",
            self.key,
            "--keyring-backend",
            "test",
            "--chain-id",
            self.chain_id,
            "--node",
            self.node,
            "--gas",
            "auto",
            "--gas-adjustment",
            "2",
            "--gas-prices",
            "0.5uakt",
            "-y",
            "-o",
            "json",
        )

    def send_manifest(self, sdl_path: Path | str, dseq: str, provider: str) -> CommandResult:
        return self._provider_services(
            "send-manifest",
            str(sdl_path),
            "--dseq",
            str(dseq),
            "--provider",
            provider,
            "--from",
            self.key,
            "--keyring-backend",
            "test",
            "--node",
            self.node,
            timeout=120,
        )

    def lease_status(self, dseq: str, provider: str) -> LeaseStatus:
        result = self._provider_services(
            "lease-status",
            "--dseq",
            str(dseq),
            "--provider",
            provider,
            "--from",
            self.key,
            "--keyring-backend",
            "test",
            "--node",
            self.node,
            "--auth-type",
            "mtls",
        )
        payload = json.loads(result.stdout)
        relay = payload.get("services", {}).get("xion-relay", {})
        forwarded = payload.get("forwarded_ports", {}).get("xion-relay", [])
        url = None
        if forwarded:
            port = forwarded[0].get("externalPort")
            host = forwarded[0].get("host")
            url = f"https://{host}:{port}" if host and port else None
        ready = relay.get("ready_replicas", 0) >= 1 and relay.get("available_replicas", 0) >= 1
        return LeaseStatus(dseq=str(dseq), provider=provider, ready=ready, forwarded_url=url, raw=payload)

    def lease_logs(self, dseq: str, provider: str, service: str = "xion-relay", tail: int = 120) -> str:
        result = self._provider_services(
            "lease-logs",
            "--dseq",
            str(dseq),
            "--provider",
            provider,
            "--from",
            self.key,
            "--keyring-backend",
            "test",
            "--node",
            self.node,
            "--auth-type",
            "mtls",
            "--service",
            service,
            "--tail",
            str(tail),
            timeout=90,
        )
        return result.stdout

    def close_deployment(self, dseq: str) -> CommandResult:
        return self._provider_services(
            "tx",
            "deployment",
            "close",
            "--dseq",
            str(dseq),
            "--from",
            self.key,
            "--keyring-backend",
            "test",
            "--chain-id",
            self.chain_id,
            "--node",
            self.node,
            "--gas",
            "auto",
            "--gas-adjustment",
            "2",
            "--gas-prices",
            "0.5uakt",
            "-y",
            "-o",
            "json",
        )

    def health_smoke(self, base_url: str, *, timeout_seconds: int = 30) -> bool:
        try:
            request = Request(base_url.rstrip("/") + "/health", method="GET")
            context = ssl._create_unverified_context()
            with urlopen(request, timeout=timeout_seconds, context=context) as response:
                return 200 <= response.status < 300
        except URLError as exc:
            raise ProviderUnreachable(str(exc)) from exc

    def deploy_relay(
        self,
        sdl_path: Path | str,
        prefer_provider: str | None = None,
        rejected_providers: set[str] | None = None,
    ) -> DeploymentResult:
        dseq: str | None = None
        provider: str | None = None
        try:
            dseq = self.create_deployment(sdl_path)
            bids = self._wait_for_bids(dseq)
            provider = prefer_provider or self._lowest_open_provider(bids, rejected_providers=rejected_providers)
            self.accept_bid(dseq, provider)
            self.send_manifest(sdl_path, dseq, provider)
            status = self._wait_for_ready(dseq, provider)
            if not status.forwarded_url:
                raise ProviderUnreachable("lease ready but no forwarded URL")
            self.health_smoke(status.forwarded_url)
            return DeploymentResult(
                service=self.name,
                ok=True,
                id=dseq,
                dseq=dseq,
                provider=provider,
                url=status.forwarded_url,
                details=status.raw,
            )
        except Exception as exc:
            if dseq:
                close = self.close_deployment(dseq)
                close_details = {"close_stdout": close.stdout, "close_stderr": close.stderr}
            else:
                close_details = {}
            return DeploymentResult(
                service=self.name,
                ok=False,
                id=dseq,
                dseq=dseq,
                provider=provider,
                details={"error": str(exc), **close_details},
            )

    def _wait_for_ready(self, dseq: str, provider: str, *, timeout_seconds: int = 900) -> LeaseStatus:
        deadline = time.monotonic() + timeout_seconds
        latest: LeaseStatus | None = None
        while time.monotonic() < deadline:
            latest = self.lease_status(dseq, provider)
            if latest.ready:
                return latest
            time.sleep(15)
        raise OpsError(f"lease {dseq} did not become ready; latest={latest}")

    def _wait_for_bids(self, dseq: str, *, timeout_seconds: int = 300) -> list[dict[str, Any]]:
        deadline = time.monotonic() + timeout_seconds
        latest: list[dict[str, Any]] = []
        while time.monotonic() < deadline:
            latest = self.list_bids(dseq)
            if any(bid.get("bid", {}).get("state") == "open" for bid in latest):
                return latest
            time.sleep(10)
        raise OpsError(f"no open Akash bids for deployment {dseq}; latest={latest}")

    def _lowest_open_provider(
        self,
        bids: list[dict[str, Any]],
        *,
        rejected_providers: set[str] | None = None,
    ) -> str:
        rejected = rejected_providers or set()
        open_bids = [
            bid
            for bid in bids
            if bid.get("bid", {}).get("state") == "open"
            and bid.get("bid", {}).get("id", {}).get("provider") not in rejected
        ]
        if not open_bids:
            raise OpsError("no open Akash bids")
        chosen = min(open_bids, key=lambda bid: float(bid["bid"]["price"]["amount"]))
        return str(chosen["bid"]["id"]["provider"])

    def _provider_services(self, *args: str, timeout: int | None = None) -> CommandResult:
        command = ["provider-services", *args]
        try:
            return run_command(command, cwd=self.repo_root, timeout=timeout)
        except FileNotFoundError:
            if os.name != "nt":
                raise
            rendered = " ".join(shlex.quote(part) for part in command)
            return run_command(
                ["wsl", "bash", "-lc", f'export PATH="$HOME/bin:$PATH"; cd /mnt/c/Users/16823/CursorProjects/xion-os; {rendered}'],
                cwd=self.repo_root,
                timeout=timeout,
            )

    def _default_owner(self) -> str:
        try:
            wallets = wallets_for_service(self.name, self.repo_root / "genesis" / "FUNDING_TARGETS.json")
        except Exception:
            return ""
        return wallets[0].address if wallets else ""

