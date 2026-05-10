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
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from xion_ops.commands import run_command
from xion_ops.exceptions import OpsError, ProviderUnreachable
from xion_ops.services.base import OpsService
from xion_ops.types import (
    BalanceReport,
    CommandResult,
    DeploymentResult,
    LeaseStatus,
    ServiceHealth,
    WalletInfo,
)
from xion_ops.wallets import wallets_for_service


def _truthy_env(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


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

    def uact_balance(self) -> float:
        amounts = {
            item["denom"]: float(item["amount"]) for item in self.query_bank_balances(self.owner).get("balances", [])
        }
        return amounts.get("uact", 0.0)

    def mint_act(self, uakt_amount: int) -> CommandResult:
        result = self._provider_services_tx(
            [
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
                *self._gas_tx_flags(),
                "-y",
                "-o",
                "json",
            ]
        )
        self._broadcast_json_confirm(result.stdout)
        return result

    def burn_act(self, uact_amount: int) -> CommandResult:
        """Burn ``uact`` to mint/remint ``uakt`` via BME (inverse of :meth:`mint_act`)."""

        result = self._provider_services_tx(
            [
                "tx",
                "bme",
                "burn-act",
                f"{uact_amount}uact",
                "--from",
                self.key,
                "--keyring-backend",
                "test",
                "--chain-id",
                self.chain_id,
                "--node",
                self.node,
                *self._gas_tx_flags(),
                "-y",
                "-o",
                "json",
            ]
        )
        self._broadcast_json_confirm(result.stdout)
        return result

    def wait_for_ledger_executed(self, *, timeout_seconds: int | None = None, poll_seconds: int | None = None) -> bool:
        timeout_seconds = timeout_seconds if timeout_seconds is not None else int(os.environ.get("XION_AKASH_BME_TIMEOUT_SEC", "600"))
        poll_seconds = poll_seconds if poll_seconds is not None else int(os.environ.get("XION_AKASH_BME_POLL_SEC", "15"))
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

    def query_cert_list(self) -> dict[str, Any]:
        result = self._provider_services(
            "query",
            "cert",
            "list",
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

    def generate_client_cert(self) -> CommandResult:
        """Official path: ``provider-services tx cert generate client``."""

        cmd = [
            "tx",
            "cert",
            "generate",
            "client",
            "--from",
            self.key,
            "--keyring-backend",
            "test",
            "--chain-id",
            self.chain_id,
            "--node",
            self.node,
            *self._gas_tx_flags(),
            "-y",
            "-o",
            "json",
        ]
        return self._provider_services_tx(cmd)

    def publish_client_cert(self) -> CommandResult:
        """Official path: ``provider-services tx cert publish client``."""

        cmd = [
            "tx",
            "cert",
            "publish",
            "client",
            "--from",
            self.key,
            "--keyring-backend",
            "test",
            "--chain-id",
            self.chain_id,
            "--node",
            self.node,
            *self._gas_tx_flags(),
            "-y",
            "-o",
            "json",
        ]
        return self._provider_services_tx(cmd)

    def ensure_client_cert_published(self) -> None:
        """Ensure an on-chain client cert exists before deployment/manifest ops."""

        payload = self.query_cert_list()
        certs = payload.get("certificates")
        if certs is None:
            certs = payload.get("certs") or []
        if not isinstance(certs, list):
            certs = []
        if len(certs) > 0:
            return
        gen = self.generate_client_cert()
        self._broadcast_json_confirm(gen.stdout)
        pub = self.publish_client_cert()
        self._broadcast_json_confirm(pub.stdout)

    def ensure_deploy_preflight(self) -> None:
        """Ensure client cert exists before on-chain deployment operations."""

        self.ensure_client_cert_published()

    def query_deployment_list(self, *, state: str | None = None) -> dict[str, Any]:
        args = [
            "query",
            "deployment",
            "list",
            "--owner",
            self.owner,
            "--node",
            self.node,
            "--chain-id",
            self.chain_id,
            "-o",
            "json",
        ]
        if state:
            args.extend(["--state", state])
        return json.loads(self._provider_services(*args).stdout)

    def query_deployment_get(self, dseq: str) -> dict[str, Any]:
        result = self._provider_services(
            "query",
            "deployment",
            "get",
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
        return json.loads(result.stdout)

    def query_market_lease_list(self, *, dseq: str | None = None, state: str | None = None) -> dict[str, Any]:
        args = [
            "query",
            "market",
            "lease",
            "list",
            "--owner",
            self.owner,
            "--node",
            self.node,
            "--chain-id",
            self.chain_id,
            "-o",
            "json",
        ]
        if dseq:
            args.extend(["--dseq", str(dseq)])
        if state:
            args.extend(["--state", state])
        return json.loads(self._provider_services(*args).stdout)

    def query_tx(self, tx_hash: str) -> dict[str, Any]:
        result = self._provider_services(
            "query",
            "tx",
            tx_hash,
            "--node",
            self.node,
            "--chain-id",
            self.chain_id,
            "-o",
            "json",
            timeout=90,
        )
        return json.loads(result.stdout)

    def update_deployment(self, sdl_path: Path | str, dseq: str) -> CommandResult:
        """On-chain deployment hash update; follow with ``send_manifest``."""

        result = self._provider_services_tx(
            [
                "tx",
                "deployment",
                "update",
                self._wsl_repo_relative_path(sdl_path),
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
                *self._gas_tx_flags(),
                "-y",
                "-o",
                "json",
            ]
        )
        self._broadcast_json_confirm(result.stdout)
        return result

    def create_deployment(self, sdl_path: Path | str) -> str:
        result = self._provider_services_tx(
            [
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
                *self._gas_tx_flags(),
                "-y",
                "-o",
                "json",
            ]
        )
        self._broadcast_json_confirm(result.stdout)
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

    def accept_bid(self, dseq: str, provider: str, *, gseq: int | None = None, oseq: int | None = None) -> CommandResult:
        gseq_val = str(gseq if gseq is not None else 1)
        oseq_val = str(oseq if oseq is not None else 1)
        return self._provider_services_tx(
            [
                "tx",
                "market",
                "lease",
                "create",
                "--dseq",
                str(dseq),
                "--gseq",
                gseq_val,
                "--oseq",
                oseq_val,
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
                *self._gas_tx_flags(),
                "-y",
                "-o",
                "json",
            ]
        )

    def send_manifest(self, sdl_path: Path | str, dseq: str, provider: str) -> CommandResult:
        sec = int(os.environ.get("XION_AKASH_SEND_MANIFEST_TIMEOUT_SEC", "120"))
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
            timeout=sec,
        )

    def lease_status(self, dseq: str, provider: str, *, service_name: str = "xion-relay") -> LeaseStatus:
        sec = int(os.environ.get("XION_AKASH_LEASE_STATUS_TIMEOUT_SEC", "0"))
        lease_timeout = sec if sec > 0 else None
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
            timeout=lease_timeout,
        )
        payload = json.loads(result.stdout)
        services = payload.get("services") or {}
        ports = payload.get("forwarded_ports") or {}
        relay = services.get(service_name, {}) or {}
        if not isinstance(relay, dict):
            relay = {}
        forwarded = ports.get(service_name, []) or []
        url = None
        if forwarded:
            port = forwarded[0].get("externalPort")
            host = forwarded[0].get("host")
            url = f"https://{host}:{port}" if host and port else None
        if not url:
            uris = relay.get("uris") or []
            if uris:
                h = str(uris[0]).strip().rstrip("/")
                if h.startswith("http://") or h.startswith("https://"):
                    url = h
                else:
                    url = f"https://{h}"
        ready = relay.get("ready_replicas", 0) >= 1 and relay.get("available_replicas", 0) >= 1
        return LeaseStatus(dseq=str(dseq), provider=provider, ready=ready, forwarded_url=url, raw=payload)

    def lease_logs(self, dseq: str, provider: str, service: str = "xion-relay", tail: int = 120) -> str:
        sec = int(os.environ.get("XION_AKASH_LEASE_LOGS_TIMEOUT_SEC", "90"))
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
            timeout=sec,
        )
        return result.stdout

    def close_deployment(self, dseq: str) -> CommandResult:
        return self._provider_services_tx(
            [
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
                *self._gas_tx_flags(),
                "-y",
                "-o",
                "json",
            ]
        )

    def health_smoke(self, base_url: str, *, timeout_seconds: int = 30) -> bool:
        """GET ``/health`` — on Windows prefer WSL ``curl`` (ingress often fails from WinSock)."""

        url = base_url.rstrip("/") + "/health"
        if os.name == "nt":
            return self._health_smoke_wsl_curl(url, timeout_seconds=timeout_seconds)
        try:
            request = Request(url, method="GET")
            context = ssl._create_unverified_context()
            with urlopen(request, timeout=timeout_seconds, context=context) as response:
                return 200 <= response.status < 300
        except URLError as exc:
            raise ProviderUnreachable(str(exc)) from exc

    def _health_smoke_wsl_curl(self, absolute_url: str, *, timeout_seconds: int) -> bool:
        """Ubuntu/WSL routing often reaches Akash nip.io ingress when native Windows stalls."""

        quoted = shlex.quote(absolute_url)
        shell = (
            f'curl -k -fsS --max-time {int(timeout_seconds)} '
            f"-o /dev/null -w \"%{{http_code}}\" {quoted}"
        )
        try:
            result = run_command(
                ["wsl", "bash", "-lc", shell],
                cwd=self.repo_root,
                timeout=timeout_seconds + 15,
            )
        except FileNotFoundError:
            request = Request(absolute_url, method="GET")
            context = ssl._create_unverified_context()
            try:
                with urlopen(request, timeout=timeout_seconds, context=context) as response:
                    return 200 <= response.status < 300
            except URLError as exc:
                raise ProviderUnreachable(str(exc)) from exc

        code = result.stdout.strip()
        return result.returncode == 0 and len(code) == 3 and code.startswith("2")

    def deploy_relay(
        self,
        sdl_path: Path | str,
        prefer_provider: str | None = None,
        rejected_providers: set[str] | None = None,
        *,
        lease_service_name: str | None = None,
    ) -> DeploymentResult:
        dseq: str | None = None
        provider: str | None = None
        svc_name = lease_service_name or os.environ.get("XION_AKASH_LEASE_SERVICE_NAME", "xion-relay")
        started = time.monotonic()
        try:
            self.ensure_deploy_preflight()
            if _truthy_env("XION_AKASH_REQUIRE_UACT"):
                minimum = float(os.environ.get("XION_AKASH_MIN_UACT", "1"))
                if self.uact_balance() < minimum:
                    raise OpsError(f"uact balance below XION_AKASH_MIN_UACT ({minimum}); fund escrow via BME mint-act.")

            dseq = self.create_deployment(sdl_path)
            bids = self._wait_for_bids(dseq)
            provider, survey, lease_orders = self._choose_reachable_provider_with_orders(
                bids,
                prefer_provider=prefer_provider,
                rejected_providers=rejected_providers,
            )
            self._append_deploy_survey(dseq, survey, chosen_provider=provider)
            for gseq, oseq in lease_orders:
                lease_tx = self.accept_bid(dseq, provider, gseq=gseq, oseq=oseq)
                self._broadcast_json_confirm(lease_tx.stdout)
            self.send_manifest(sdl_path, dseq, provider)
            ready_sec = int(os.environ.get("XION_AKASH_WAIT_READY_SEC", "900"))
            status = self._wait_for_ready(dseq, provider, timeout_seconds=ready_sec, service_name=svc_name)
            if not status.forwarded_url:
                raise ProviderUnreachable("lease ready but no forwarded URL")
            self.health_smoke(status.forwarded_url, timeout_seconds=int(os.environ.get("XION_AKASH_HEALTH_SMOKE_SEC", "120")))
            return DeploymentResult(
                service=self.name,
                ok=True,
                id=dseq,
                dseq=dseq,
                provider=provider,
                url=status.forwarded_url,
                details={
                    **status.raw,
                    "duration_s": round(time.monotonic() - started, 3),
                    "survey_count": len(survey)
                },
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
                details={"error": str(exc), "duration_s": round(time.monotonic() - started, 3), **close_details},
            )

    def _wait_for_ready(
        self,
        dseq: str,
        provider: str,
        *,
        timeout_seconds: int = 900,
        service_name: str = "xion-relay",
    ) -> LeaseStatus:
        poll = float(os.environ.get("XION_AKASH_READY_POLL_SEC", "15"))
        deadline = time.monotonic() + timeout_seconds
        latest: LeaseStatus | None = None
        while time.monotonic() < deadline:
            latest = self.lease_status(dseq, provider, service_name=service_name)
            if latest.ready and latest.forwarded_url:
                return latest
            time.sleep(poll)
        raise OpsError(f"lease {dseq} did not become ready with a URL; latest={latest}")

    def _wait_for_bids(self, dseq: str, *, timeout_seconds: int | None = None) -> list[dict[str, Any]]:
        timeout_seconds = timeout_seconds if timeout_seconds is not None else int(os.environ.get("XION_AKASH_BID_WAIT_SEC", "300"))
        poll = float(os.environ.get("XION_AKASH_BID_POLL_SEC", "10"))
        delay_first = float(os.environ.get("XION_AKASH_FIRST_BID_DELAY_SEC", "25"))
        time.sleep(delay_first)
        deadline = time.monotonic() + timeout_seconds
        latest: list[dict[str, Any]] = []
        while time.monotonic() < deadline:
            latest = self.list_bids(dseq)
            if any(bid.get("bid", {}).get("state") == "open" for bid in latest):
                return latest
            time.sleep(poll)
        raise OpsError(f"no open Akash bids for deployment {dseq}; latest={latest}")

    def _bid_gseq_oseq(self, bid_body: dict[str, Any]) -> tuple[int, int]:
        bid_id = bid_body.get("id") or {}
        raw_g = bid_id.get("gseq", 1)
        raw_o = bid_id.get("oseq", 1)
        return int(str(raw_g)), int(str(raw_o))

    def _open_orders_for_provider(self, bids: list[dict[str, Any]], provider: str) -> list[tuple[int, int]]:
        rows: list[tuple[int, int]] = []
        for bid in bids:
            body = bid.get("bid", {})
            if body.get("state") != "open":
                continue
            bid_id = body.get("id", {})
            if bid_id.get("provider") != provider:
                continue
            rows.append(self._bid_gseq_oseq(body))
        rows = sorted(set(rows), key=lambda t: (t[0], t[1]))
        return rows

    def _providers_sorted_by_total_open_price(self, bids: list[dict[str, Any]], rejected: set[str]) -> list[str]:
        totals: dict[str, float] = {}
        for bid in bids:
            body = bid.get("bid", {})
            if body.get("state") != "open":
                continue
            prov = body.get("id", {}).get("provider")
            if not prov or prov in rejected:
                continue
            amt = float(body.get("price", {}).get("amount", "0"))
            totals[str(prov)] = totals.get(str(prov), 0.0) + amt
        return sorted(totals.keys(), key=lambda p: totals[p])

    def _choose_reachable_provider_with_orders(
        self,
        bids: list[dict[str, Any]],
        *,
        prefer_provider: str | None = None,
        rejected_providers: set[str] | None = None,
    ) -> tuple[str, list[dict[str, Any]], list[tuple[int, int]]]:
        rejected = rejected_providers or set()
        survey: list[dict[str, Any]] = []

        ordered_providers = self._providers_sorted_by_total_open_price(bids, rejected)
        if prefer_provider:
            if prefer_provider in rejected:
                raise OpsError(f"preferred provider {prefer_provider!r} is excluded")
            ordered_providers = [prefer_provider] + [p for p in ordered_providers if p != prefer_provider]

        for candidate in ordered_providers:
            lease_orders = self._open_orders_for_provider(bids, candidate)
            if not lease_orders:
                continue
            allowlisted = candidate in self.provider_allowlist
            reachable = allowlisted or self._provider_ingress_reachable(candidate)
            survey.append(
                {
                    "provider": candidate,
                    "lease_orders": lease_orders,
                    "allowlisted": allowlisted,
                    "pre_accept_reachable": reachable,
                    "decision": "accept" if reachable else "skip_unreachable_provider_ingress",
                }
            )
            if reachable:
                return candidate, survey, lease_orders

        raise OpsError(f"no reachable Akash provider ingress among open bids; surveyed={survey}")

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

    def _gas_tx_flags(self) -> list[str]:
        gas = os.environ.get("AKASH_GAS", "auto")
        adjustment = os.environ.get("AKASH_GAS_ADJUSTMENT", "2")
        prices = os.environ.get("AKASH_GAS_PRICES", "0.5uakt")
        return ["--gas", gas, "--gas-adjustment", adjustment, "--gas-prices", prices]

    def _broadcast_json_confirm(self, stdout: str) -> dict[str, Any]:
        payload = json.loads(stdout)
        code = payload.get("code")
        if code is not None and int(str(code)) != 0:
            raise OpsError(
                "akash tx rejected "
                f"code={code} codespace={payload.get('codespace')} raw_log={payload.get('raw_log')}"
            )
        if _truthy_env("XION_AKASH_WAIT_TX", default=True):
            txhash = payload.get("txhash")
            if txhash:
                self._wait_tx_hash(str(txhash))
        return payload

    def _wait_tx_hash(self, tx_hash: str) -> None:
        deadline_sec = float(os.environ.get("XION_AKASH_TX_WAIT_SEC", "120"))
        poll_sec = float(os.environ.get("XION_AKASH_TX_POLL_SEC", "2"))
        deadline = time.monotonic() + deadline_sec
        while time.monotonic() < deadline:
            try:
                row = self.query_tx(tx_hash)
            except Exception:
                time.sleep(poll_sec)
                continue
            height = row.get("height")
            if height is not None and str(height) not in ("0", ""):
                code = row.get("code")
                if code is not None and int(str(code)) != 0:
                    raise OpsError(f"included tx failed code={code}: {tx_hash}")
                return
            time.sleep(poll_sec)
        raise OpsError(f"timeout waiting for tx inclusion: {tx_hash}")

    def _provider_services_tx(self, argv: list[str]) -> CommandResult:
        """Invoke ``provider-services`` with tx argv (gas flags already embedded)."""

        return self._provider_services(*argv, timeout=int(os.environ.get("XION_AKASH_TX_CMD_TIMEOUT_SEC", "180")))

    def _provider_services(self, *args: str, timeout: int | None = None) -> CommandResult:
        command = ["provider-services", *args]
        try:
            return run_command(command, cwd=self.repo_root, timeout=timeout)
        except FileNotFoundError:
            if os.name != "nt":
                raise
            rendered = " ".join(shlex.quote(part) for part in command)
            wsl_cd = self._wsl_repo_cd_path()
            return run_command(
                ["wsl", "bash", "-lc", f'export PATH="$HOME/bin:$PATH"; cd {shlex.quote(wsl_cd)}; {rendered}'],
                cwd=self.repo_root,
                timeout=timeout,
            )

    def _wsl_repo_cd_path(self) -> str:
        override = os.environ.get("AKASH_WSL_REPO")
        if override:
            return override.strip().rstrip("/")
        return _windows_repo_to_wsl_cd(self.repo_root)

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


def _windows_repo_to_wsl_cd(repo_root: Path | str) -> str:
    resolved = Path(repo_root).resolve()
    if os.name != "nt":
        return str(resolved).replace("\\", "/")
    drive = resolved.drive
    if len(drive) >= 2 and drive[1] == ":":
        letter = drive[0].lower()
        tail = "/".join(str(p).replace("\\", "/") for p in resolved.parts[1:]) if len(resolved.parts) > 1 else ""
        prefix = f"/mnt/{letter}"
        return f"{prefix}/{tail}" if tail else prefix
    return str(resolved).replace("\\", "/")

