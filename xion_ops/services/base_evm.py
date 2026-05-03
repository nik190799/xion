"""Base EVM operational service."""

from __future__ import annotations

import json
import os
import time
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from xion_ops.commands import run_command
from xion_ops.exceptions import OpsError
from xion_ops.services.base import OpsService
from xion_ops.types import BalanceReport, CommandResult, DeploymentResult, ServiceHealth, WalletInfo
from xion_ops.wallets import wallets_for_service


class BaseEvmService(OpsService):
    name = "base-evm"

    DEFAULT_RPCS = {
        "base": "https://mainnet.base.org",
        "base-mainnet": "https://mainnet.base.org",
        "base-sepolia": "https://sepolia.base.org",
    }

    def addresses(self) -> list[WalletInfo]:
        return wallets_for_service(self.name, self.repo_root / "genesis" / "FUNDING_TARGETS.json")

    def balances(self) -> list[BalanceReport]:
        reports: list[BalanceReport] = []
        for wallet in self.addresses():
            try:
                balance = self.eth_balance(wallet.address, wallet.network)
                status = "ok" if balance >= wallet.target else ("zero" if balance == 0 else "shortfall")
                reports.append(
                    BalanceReport(
                        wallet=wallet,
                        balance=balance,
                        raw_balance=str(balance),
                        status=status,
                    )
                )
            except Exception as exc:
                reports.append(BalanceReport(wallet=wallet, balance=None, status="unknown", message=str(exc)))
        return reports

    def health(self) -> ServiceHealth:
        try:
            rpc = self.rpc_url("base-sepolia")
            payload = {"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1}
            response = self._rpc(rpc, payload)
            return ServiceHealth(service=self.name, ok="result" in response, details={"rpc": rpc})
        except Exception as exc:
            return ServiceHealth(service=self.name, ok=False, message=str(exc))

    def eth_balance(self, address: str, network: str) -> float:
        rpc = self.rpc_url(network)
        payload = {"jsonrpc": "2.0", "method": "eth_getBalance", "params": [address, "latest"], "id": 1}
        response = self._rpc(rpc, payload)
        result = response.get("result")
        if not isinstance(result, str) or not result.startswith("0x"):
            raise OpsError(f"invalid eth_getBalance response for {address}: {response}")
        wei = int(result, 16)
        return float(Decimal(wei) / Decimal(10**18))

    def wait_for_funding(
        self,
        address: str,
        target_eth: float,
        network: str,
        *,
        poll_seconds: int = 15,
        timeout_seconds: int = 900,
    ) -> bool:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            if self.eth_balance(address, network) >= target_eth:
                return True
            time.sleep(poll_seconds)
        return False

    def forge_deploy(self, script: str, network: str, *, broadcast: bool = True) -> CommandResult:
        command = ["forge", "script", script, "--rpc-url", self.rpc_url(network)]
        if broadcast:
            command.append("--broadcast")
        return run_command(command, cwd=self.repo_root)

    def cast_send(self, *args: str, network: str) -> CommandResult:
        return run_command(["cast", "send", "--rpc-url", self.rpc_url(network), *args], cwd=self.repo_root)

    def cast_call(self, *args: str, network: str) -> CommandResult:
        return run_command(["cast", "call", "--rpc-url", self.rpc_url(network), *args], cwd=self.repo_root)

    def deploy_treasury(self, network: str = "base", script: str = "treasury/script/Deploy.s.sol:DeployTreasury") -> DeploymentResult:
        result = self.forge_deploy(script, network, broadcast=True)
        return DeploymentResult(service=self.name, ok=True, id="treasury", details={"stdout": result.stdout})

    def deploy_vault(self, network: str, *cast_args: str) -> DeploymentResult:
        result = self.cast_send(*cast_args, network=network)
        return DeploymentResult(service=self.name, ok=True, id="vault", details={"stdout": result.stdout})

    def safe_propose_tx(self, *_args: Any, **_kwargs: Any) -> DeploymentResult:
        raise NotImplementedError(
            "BaseEvmService.safe_propose_tx is intentionally stubbed; see KW-OPS-001."
        )

    def rpc_url(self, network: str) -> str:
        env_key = {
            "base": "BASE_MAINNET_RPC",
            "base-mainnet": "BASE_MAINNET_RPC",
            "base-sepolia": "BASE_SEPOLIA_RPC",
        }.get(network)
        if env_key and os.environ.get(env_key):
            return os.environ[env_key]
        return self.DEFAULT_RPCS.get(network, network)

    @staticmethod
    def _rpc(rpc_url: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = Request(
            rpc_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))

