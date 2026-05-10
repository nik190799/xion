"""Base EVM operational service."""

from __future__ import annotations

import json
import os
import re
import shlex
import time
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from xion_ops.commands import run_command
from xion_ops.exceptions import CommandFailed, OpsError
from xion_ops.services.base import OpsService
from xion_ops.types import BalanceReport, CommandResult, DeploymentResult, ServiceHealth, WalletInfo
from xion_ops.wallets import wallets_for_service

# Same address as ``prepare-sepolia-env`` in ``cli.py`` — safe for Sepolia rehearsal only.
_MAINNET_FORBIDDEN_GOVERNANCE = "0xEBDDDf598b5b53C91ff185501d7b182ae5d6B88A"


class BaseEvmService(OpsService):
    name = "base-evm"

    DEFAULT_RPCS = {
        "base": (
            "https://mainnet.base.org",
            "https://base-rpc.publicnode.com",
            "https://base.llamarpc.com",
        ),
        "base-mainnet": (
            "https://mainnet.base.org",
            "https://base-rpc.publicnode.com",
            "https://base.llamarpc.com",
        ),
        "base-sepolia": (
            "https://sepolia.base.org",
            "https://base-sepolia-rpc.publicnode.com",
        ),
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
            payload = {"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1}
            rpc, response = self._rpc_any(self.rpc_urls("base-sepolia"), payload)
            return ServiceHealth(service=self.name, ok="result" in response, details={"rpc": rpc})
        except Exception as exc:
            return ServiceHealth(service=self.name, ok=False, message=str(exc))

    def eth_balance(self, address: str, network: str) -> float:
        payload = {"jsonrpc": "2.0", "method": "eth_getBalance", "params": [address, "latest"], "id": 1}
        _rpc, response = self._rpc_any(self.rpc_urls(network), payload)
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
        cwd = self.repo_root / "contracts" if (self.repo_root / "contracts" / "foundry.toml").exists() else self.repo_root
        script_arg = script.removeprefix("contracts/")
        command = ["forge", "script", script_arg, "--rpc-url", self.rpc_url(network)]
        if broadcast:
            command.append("--broadcast")
        private_key = os.environ.get("PRIVATE_KEY") or os.environ.get("XION_DEPLOYER_PRIVATE_KEY")
        if private_key:
            command.extend(["--private-key", private_key])
        return self._run_foundry(command, cwd=cwd)

    def cast_send(self, *args: str, network: str) -> CommandResult:
        command = ["cast", "send", "--rpc-url", self.rpc_url(network), *args]
        private_key = os.environ.get("PRIVATE_KEY") or os.environ.get("XION_DEPLOYER_PRIVATE_KEY")
        if private_key and "--private-key" not in command:
            command.extend(["--private-key", private_key])
        return self._run_foundry(command)

    def cast_call(self, *args: str, network: str) -> CommandResult:
        return self._run_foundry(["cast", "call", "--rpc-url", self.rpc_url(network), *args])

    def treasury_deploy_preflight_issues(self, network: str) -> list[str]:
        """Return human-readable blockers before ``forge script`` broadcast."""

        issues: list[str] = []
        pk = (os.environ.get("PRIVATE_KEY") or os.environ.get("XION_DEPLOYER_PRIVATE_KEY") or "").strip()
        if not pk:
            issues.append(
                "Missing PRIVATE_KEY or XION_DEPLOYER_PRIVATE_KEY "
                "(set in repo-root .env; see docs/runbooks/TREASURY_SEPOLIA_DEPLOY.md)"
            )
        if network not in ("base-sepolia", "base", "base-mainnet"):
            issues.append(f"Unknown network {network!r} for treasury preflight")
            return issues
        if network == "base-sepolia":
            if not os.environ.get("XION_TREASURY_GOVERNANCE", "").strip():
                issues.append(
                    "Missing XION_TREASURY_GOVERNANCE (run: python -m xion_ops.cli base-evm prepare-sepolia-env)"
                )
            if not os.environ.get("XION_AO_CORE_AUTHORITY", "").strip():
                issues.append(
                    "Missing XION_AO_CORE_AUTHORITY (run: python -m xion_ops.cli base-evm prepare-sepolia-env)"
                )
            cap = os.environ.get("XION_BRIDGE_CAP_BPS", "").strip()
            if not cap:
                issues.append(
                    "Missing XION_BRIDGE_CAP_BPS (run: python -m xion_ops.cli base-evm prepare-sepolia-env)"
                )
        if network in ("base", "base-mainnet"):
            gov = os.environ.get("XION_TREASURY_GOVERNANCE", "").strip()
            if not gov:
                issues.append(
                    "Missing XION_TREASURY_GOVERNANCE (set production governance / Safe; "
                    "see docs/runbooks/TREASURY_BASE_MAINNET_DEPLOY.md)"
                )
            elif gov.lower() == _MAINNET_FORBIDDEN_GOVERNANCE.lower():
                issues.append(
                    "XION_TREASURY_GOVERNANCE is the prepare-sepolia-env rehearsal default — "
                    "not valid for Base mainnet; set Cold Root / Warm Safe governance"
                )
            if not os.environ.get("XION_AO_CORE_AUTHORITY", "").strip():
                issues.append(
                    "Missing XION_AO_CORE_AUTHORITY (set production AO authority; "
                    "see docs/runbooks/TREASURY_BASE_MAINNET_DEPLOY.md)"
                )
            cap = os.environ.get("XION_BRIDGE_CAP_BPS", "").strip()
            if not cap:
                issues.append("Missing XION_BRIDGE_CAP_BPS")
        return issues

    def deploy_treasury(self, network: str = "base-sepolia", script: str = "treasury/script/Deploy.s.sol:DeployTreasury") -> DeploymentResult:
        """Broadcast ``DeployTreasury`` via Foundry.

        Defaults to ``base-sepolia`` so operators do not accidental-broadcast Mainnet ``base``.
        """

        pre = self.treasury_deploy_preflight_issues(network)
        if pre:
            return DeploymentResult(
                service=self.name,
                ok=False,
                id="treasury",
                details={"error": "; ".join(pre), "preflight_issues": pre},
            )
        try:
            result = self.forge_deploy(script, network, broadcast=True)
        except CommandFailed as exc:
            return DeploymentResult(
                service=self.name,
                ok=False,
                id="treasury",
                details={"error": str(exc)},
            )

        details: dict[str, Any] = {"stdout": result.stdout, "stderr": result.stderr}
        details.update(self._deployment_details_from_broadcast(network))
        master = details.get("master_treasury")
        ok_addr = isinstance(master, str) and master.startswith("0x") and len(master) >= 42
        if not ok_addr:
            return DeploymentResult(
                service=self.name,
                ok=False,
                id="treasury",
                details={**details, "error": "MasterTreasury address missing from forge broadcast receipts"},
            )
        return DeploymentResult(
            service=self.name,
            ok=True,
            id=master,
            tx=details.get("master_treasury_deploy_tx"),
            details=details,
        )

    def deploy_vault(self, network: str, *cast_args: str) -> DeploymentResult:
        result = self.cast_send(*cast_args, network=network)
        return DeploymentResult(service=self.name, ok=True, id="vault", details={"stdout": result.stdout})

    def safe_compute_tx_hash(
        self,
        *,
        network: str,
        safe_address: str,
        to: str,
        data: bytes,
        value: int = 0,
        operation: int = 0,
        nonce: int | None = None,
        safe_tx_gas: int = 0,
        base_gas: int = 0,
        gas_price: int = 0,
        gas_token: str = "0x" + "00" * 20,
        refund_receiver: str = "0x" + "00" * 20,
    ) -> dict[str, Any]:
        """Build a SafeTx and compute its EIP-712 hash, without signing.

        The operator signs the returned ``safe_tx_hash`` through the Safe app
        or ``cast wallet sign --data <typed_data_json>`` and then passes the
        signature back into :py:meth:`safe_propose_tx`.
        """

        from xion_ops.services import safe as _safe

        if network not in _safe.CHAIN_IDS:
            raise OpsError(f"unsupported network for Safe: {network!r}")
        chain_id = _safe.CHAIN_IDS[network]

        if nonce is None:
            client = _safe.SafeTxServiceClient(network=network)
            nonce = client.fetch_next_nonce(safe_address)

        tx = _safe.SafeTx(
            to=to,
            value=value,
            data=data,
            operation=operation,
            safe_tx_gas=safe_tx_gas,
            base_gas=base_gas,
            gas_price=gas_price,
            gas_token=gas_token,
            refund_receiver=refund_receiver,
            nonce=nonce,
        )
        keccak = _safe.make_cast_keccak(self._run_foundry)
        tx_hash = _safe.safe_tx_hash(
            tx,
            chain_id=chain_id,
            safe_address=safe_address,
            keccak=keccak,
        )
        return {
            "safe_tx_hash": "0x" + tx_hash.hex(),
            "chain_id": chain_id,
            "safe_address": safe_address,
            "nonce": nonce,
            "tx": {
                "to": tx.to,
                "value": str(tx.value),
                "data": "0x" + tx.data.hex(),
                "operation": tx.operation,
                "safeTxGas": str(tx.safe_tx_gas),
                "baseGas": str(tx.base_gas),
                "gasPrice": str(tx.gas_price),
                "gasToken": tx.gas_token,
                "refundReceiver": tx.refund_receiver,
                "nonce": tx.nonce,
            },
        }

    def safe_propose_tx(
        self,
        *,
        network: str,
        safe_address: str,
        to: str,
        data: bytes,
        sender: str,
        signature: str,
        value: int = 0,
        operation: int = 0,
        nonce: int | None = None,
        safe_tx_gas: int = 0,
        base_gas: int = 0,
        gas_price: int = 0,
        gas_token: str = "0x" + "00" * 20,
        refund_receiver: str = "0x" + "00" * 20,
    ) -> DeploymentResult:
        """Submit an unsigned SafeTx + proposer signature to the Safe service.

        Closes KW-OPS-001 (boundary surface). The proposer signature is what
        the Safe Transaction Service uses to authenticate the proposal; the
        SafeTx itself still needs ``threshold`` cosignatures collected through
        the Safe app before it can be executed.
        """

        from xion_ops.services import safe as _safe

        prep = self.safe_compute_tx_hash(
            network=network,
            safe_address=safe_address,
            to=to,
            data=data,
            value=value,
            operation=operation,
            nonce=nonce,
            safe_tx_gas=safe_tx_gas,
            base_gas=base_gas,
            gas_price=gas_price,
            gas_token=gas_token,
            refund_receiver=refund_receiver,
        )
        tx = _safe.SafeTx(
            to=to,
            value=value,
            data=data,
            operation=operation,
            safe_tx_gas=safe_tx_gas,
            base_gas=base_gas,
            gas_price=gas_price,
            gas_token=gas_token,
            refund_receiver=refund_receiver,
            nonce=prep["nonce"],
        )
        client = _safe.SafeTxServiceClient(network=network)
        try:
            proposed = client.propose(
                safe_address=safe_address,
                safe_tx=tx,
                safe_tx_hash_hex=prep["safe_tx_hash"],
                sender=sender,
                signature=signature,
            )
        except _safe.SafeError as exc:
            return DeploymentResult(
                service=self.name,
                ok=False,
                id="safe-propose",
                details={"error": str(exc), **prep},
            )
        return DeploymentResult(
            service=self.name,
            ok=True,
            id=proposed.safe_tx_hash,
            details={
                "safe_tx_hash": proposed.safe_tx_hash,
                "nonce": proposed.nonce,
                "api_url": proposed.api_url,
                "service_response": dict(proposed.response),
                "chain_id": prep["chain_id"],
            },
        )

    def pin_treasury_deployment(self, manifest: Path | str, *, address: str, tx: str, block: int) -> None:
        path = self.repo_root / manifest
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["master_treasury"] = address
        payload["master_treasury_deploy_tx"] = tx
        payload["master_treasury_deploy_block"] = block
        residual = str(payload.get("residual", ""))
        payload["residual"] = residual.replace(
            "The pinned Base Sepolia deployment predates the current MasterTreasury source interface.",
            "The pinned Base Sepolia deployment was refreshed from the current MasterTreasury source interface.",
        )
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        tmp.replace(path)

    def rotation_rehearsal(
        self,
        *,
        network: str,
        master_treasury: str,
        count: int = 3,
    ) -> list[dict[str, Any]]:
        proposed = [
            "0x000000000000000000000000000000000000bEEF",
            "0x000000000000000000000000000000000000CAFE",
            "0x000000000000000000000000000000000000dEaD",
        ][:count]
        rows: list[dict[str, Any]] = []
        for address in proposed:
            result = self.cast_send(
                master_treasury,
                "proposeAuthorityRotation(address)",
                address,
                network=network,
            )
            rows.append({"proposed_authority": address, "tx": self._parse_tx_hash(result.stdout), "stdout": result.stdout})
        self._append_rotation_rehearsal(network=network, master_treasury=master_treasury, rows=rows)
        return rows

    def rpc_url(self, network: str) -> str:
        return self.rpc_urls(network)[0]

    def rpc_urls(self, network: str) -> list[str]:
        env_key = {
            "base": "BASE_MAINNET_RPC",
            "base-mainnet": "BASE_MAINNET_RPC",
            "base-sepolia": "BASE_SEPOLIA_RPC",
        }.get(network)
        env_keys = [
            env_key,
            f"XION_{network.upper().replace('-', '_')}_RPC",
            f"{network.upper().replace('-', '_')}_RPC_URL",
        ]
        configured = [os.environ[key] for key in env_keys if key and os.environ.get(key)]
        defaults = self.DEFAULT_RPCS.get(network, (network,))
        if isinstance(defaults, str):
            defaults = (defaults,)
        return [*configured, *defaults]

    @classmethod
    def _rpc_any(cls, rpc_urls: list[str], payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        errors: list[str] = []
        for rpc_url in rpc_urls:
            try:
                return rpc_url, cls._rpc(rpc_url, payload)
            except Exception as exc:
                errors.append(f"{rpc_url}: {exc}")
        raise OpsError("; ".join(errors))

    @staticmethod
    def _rpc(rpc_url: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = Request(
            rpc_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "xion-ops/0.1"},
            method="POST",
        )
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))

    def _run_foundry(self, command: list[str], *, cwd: Path | None = None) -> CommandResult:
        working_dir = cwd or self.repo_root
        try:
            return run_command(command, cwd=working_dir)
        except FileNotFoundError:
            if os.name != "nt":
                raise
            rendered = " ".join(shlex.quote(part) for part in command)
            wsl_cwd = str(working_dir).replace("\\", "/").replace("C:", "/mnt/c")
            exports = " ".join(
                f"export {key}={shlex.quote(value)};"
                for key in (
                    "PRIVATE_KEY",
                    "XION_DEPLOYER_PRIVATE_KEY",
                    "XION_TREASURY_GOVERNANCE",
                    "XION_AO_CORE_AUTHORITY",
                    "XION_BRIDGE_CAP_BPS",
                    "BASE_SEPOLIA_RPC",
                    "XION_BASE_SEPOLIA_RPC",
                    "BASE_SEPOLIA_RPC_URL",
                )
                if (value := os.environ.get(key))
            )
            return run_command(
                [
                    "wsl",
                    "bash",
                    "-lc",
                    f'export PATH="$HOME/.foundry/bin:$PATH"; {exports} cd {shlex.quote(wsl_cwd)}; {rendered}',
                ],
                cwd=self.repo_root,
            )

    def _deployment_details_from_broadcast(self, network: str) -> dict[str, Any]:
        chain_id = {"base-sepolia": "84532", "base": "8453", "base-mainnet": "8453"}.get(network)
        if not chain_id:
            return {}
        broadcast_root = self.repo_root / "contracts" / "broadcast"
        candidates = sorted(
            broadcast_root.glob(f"**/{chain_id}/run-latest.json"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if not candidates:
            return {}
        try:
            payload = json.loads(candidates[0].read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        details: dict[str, Any] = {"broadcast_file": str(candidates[0])}
        for tx in payload.get("transactions", []):
            if tx.get("contractName") == "MasterTreasury" and tx.get("contractAddress"):
                details["master_treasury"] = tx["contractAddress"]
                details["master_treasury_deploy_tx"] = tx.get("hash")
                break
        for receipt in payload.get("receipts", []):
            block_number = receipt.get("blockNumber")
            if isinstance(block_number, str) and block_number.startswith("0x"):
                details["master_treasury_deploy_block"] = int(block_number, 16)
                break
            if isinstance(block_number, int):
                details["master_treasury_deploy_block"] = block_number
                break
        return {key: value for key, value in details.items() if value is not None}

    def _append_rotation_rehearsal(
        self,
        *,
        network: str,
        master_treasury: str,
        rows: list[dict[str, Any]],
    ) -> None:
        path = self.repo_root / "ledgers" / "ROTATION_REHEARSAL_LEDGER.jsonl"
        payload = {
            "schema_version": 1,
            "as_of_utc_ns": time.time_ns(),
            "network": network,
            "master_treasury": master_treasury,
            "calls": rows,
        }
        path.open("a", encoding="utf-8").write(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")

    @staticmethod
    def _parse_tx_hash(stdout: str) -> str | None:
        match = re.search(r"0x[a-fA-F0-9]{64}", stdout)
        return match.group(0) if match else None

