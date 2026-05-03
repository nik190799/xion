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
from urllib.parse import urlparse
from urllib.error import URLError
from urllib.request import Request, urlopen

from xion_ops.commands import run_command
from xion_ops.exceptions import OpsError, ProviderUnreachable
from xion_ops.services.base import OpsService
from xion_ops.types import BalanceReport, CommandResult, DeploymentResult, LeaseStatus, ServiceHealth, WalletInfo
from xion_ops.wallets import wallets_for_service


class AkashService(OpsService):
    name = "akash"

    def __init__(
        self,
        *,
        repo_root: Path | str = ".",
        key: str | None = None,
        node: str | None = None,
        provider_allowlist: set[str] | None = None,
    ) -> None:
        super().__init__(repo_root=repo_root)
        self.key = key or os.environ.get("XION_AKASH_KEY", "xion-b5")
        self.node = node or os.environ.get("AKASH_NODE", "https://rpc.akashnet.net:443")
        self.chain_id = os.environ.get("AKASH_CHAIN_ID", "akashnet-2")
        self.owner = os.environ.get("XION_AKASH_OWNER", self._default_owner())
        self.provider_allowlist = provider_allowlist if provider_allowlist is not None else self._load_provider_allowlist()

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
            self._wsl_repo_relative_path(sdl_path),
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

    def provider_host_uri(self, provider: str) -> str | None:
        result = self._provider_services(
            "query",
            "provider",
            "get",
            provider,
            "--node",
            self.node,
            "--chain-id",
            self.chain_id,
            "-o",
            "json",
        )
        payload = json.loads(result.stdout)
        info = payload.get("provider", payload)
        return (
            info.get("host_uri")
            or info.get("hostUri")
            or info.get("hostURI")
            or payload.get("host_uri")
            or payload.get("hostUri")
        )

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
            self._wsl_repo_relative_path(sdl_path),
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
            provider, survey = self._choose_reachable_provider(
                bids,
                prefer_provider=prefer_provider,
                rejected_providers=rejected_providers,
            )
            self._append_deploy_survey(dseq, survey, chosen_provider=provider)
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
            if dseq and provider is None:
                self._append_deploy_survey(dseq, [], chosen_provider=None, error=str(exc))
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

    def _choose_reachable_provider(
        self,
        bids: list[dict[str, Any]],
        *,
        prefer_provider: str | None = None,
        rejected_providers: set[str] | None = None,
    ) -> tuple[str, list[dict[str, Any]]]:
        candidates = self._open_bids_by_price(bids, rejected_providers=rejected_providers)
        if prefer_provider:
            candidates = [bid for bid in candidates if bid["provider"] == prefer_provider]
        survey: list[dict[str, Any]] = []
        for bid in candidates:
            provider = str(bid["provider"])
            allowlisted = provider in self.provider_allowlist
            reachable = allowlisted or self._provider_ingress_reachable(provider)
            survey.append(
                {
                    "provider": provider,
                    "price": bid["price"],
                    "allowlisted": allowlisted,
                    "pre_accept_reachable": reachable,
                    "decision": "accept" if reachable else "skip_unreachable_provider_ingress",
                }
            )
            if reachable:
                return provider, survey
        raise OpsError(f"no reachable Akash provider ingress among open bids; surveyed={survey}")

    def _open_bids_by_price(
        self,
        bids: list[dict[str, Any]],
        *,
        rejected_providers: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        rejected = rejected_providers or set()
        candidates: list[dict[str, Any]] = []
        for bid in bids:
            bid_body = bid.get("bid", {})
            provider = bid_body.get("id", {}).get("provider")
            if bid_body.get("state") != "open" or not provider or provider in rejected:
                continue
            candidates.append({"provider": str(provider), "price": str(bid_body.get("price", {}).get("amount", "0"))})
        return sorted(candidates, key=lambda bid: float(bid["price"]))

    def _provider_ingress_reachable(self, provider: str) -> bool:
        try:
            host_uri = self.provider_host_uri(provider)
            if not host_uri:
                return False
            parsed = urlparse(host_uri if "://" in host_uri else f"https://{host_uri}")
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            request = Request(base_url.rstrip("/") + "/status", method="GET")
            context = ssl._create_unverified_context()
            with urlopen(request, timeout=8, context=context) as response:
                return 200 <= response.status < 500
        except Exception:
            return False

    def _append_deploy_survey(
        self,
        dseq: str,
        survey: list[dict[str, Any]],
        *,
        chosen_provider: str | None,
        error: str | None = None,
    ) -> None:
        path = self.repo_root / "ledgers" / "AKASH_DEPLOY_SURVEY_LEDGER.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        row = {
            "schema_version": 1,
            "as_of_utc_ns": time.time_ns(),
            "dseq": str(dseq),
            "chosen_provider": chosen_provider,
            "survey": survey,
            "error": error,
        }
        path.open("a", encoding="utf-8").write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")

    def _load_provider_allowlist(self) -> set[str]:
        path = self.repo_root / "genesis" / "PROVIDER_ALLOWLIST.json"
        if not path.is_file():
            return set()
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return set()
        providers = payload.get("providers", [])
        if not isinstance(providers, list):
            return set()
        return {
            str(item.get("provider"))
            for item in providers
            if isinstance(item, dict) and isinstance(item.get("provider"), str) and item.get("provider")
        }

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

    def _wsl_repo_relative_path(self, path: Path | str) -> str:
        candidate = Path(path)
        try:
            candidate = candidate.resolve().relative_to(self.repo_root.resolve())
        except ValueError:
            pass
        return candidate.as_posix()

