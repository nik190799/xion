"""Chutes operational service."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from xion_ops.commands import run_command
from xion_ops.services.base import OpsService
from xion_ops.types import BalanceReport, DeploymentResult, ServiceHealth, WalletInfo
from xion_ops.wallets import wallets_for_service


class ChutesService(OpsService):
    name = "chutes"

    def addresses(self) -> list[WalletInfo]:
        registry = self.repo_root / "genesis" / "FUNDING_TARGETS.json"
        if not registry.exists():
            return []
        return wallets_for_service(self.name, registry)

    def balances(self) -> list[BalanceReport]:
        reports: list[BalanceReport] = []
        for wallet in self.addresses():
            try:
                balance = self.credit_balance()
                status = "ok" if balance >= wallet.target else ("zero" if balance == 0 else "shortfall")
                reports.append(BalanceReport(wallet=wallet, balance=balance, raw_balance=str(balance), status=status))
            except Exception as exc:
                reports.append(BalanceReport(wallet=wallet, balance=None, status="unknown", message=str(exc)))
        return reports

    def health(self, url: str | None = None) -> ServiceHealth:
        target = url or os.environ.get("XION_CHUTES_HEALTH_URL") or self.base_url()
        if not target:
            return ServiceHealth(service=self.name, ok=False, message="no Chutes URL configured")
        try:
            with urlopen(target.rstrip("/") + "/health", timeout=20) as response:
                return ServiceHealth(service=self.name, ok=200 <= response.status < 300, details={"url": target})
        except Exception as exc:
            return ServiceHealth(service=self.name, ok=False, message=str(exc), details={"url": target})

    def credit_balance(self) -> float:
        api_url = os.environ.get("XION_CHUTES_CREDITS_URL")
        token = os.environ.get("CHUTES_API_KEY") or os.environ.get("XION_CHUTES_API_KEY")
        if not api_url:
            return 0.0
        request = Request(api_url, headers={"Authorization": f"Bearer {token}"} if token else {})
        with urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return float(payload.get("balance") or payload.get("credits") or payload.get("balance_usd") or 0)

    def verify_cords(self, url: str | None = None) -> DeploymentResult:
        target = url or self.base_url()
        health = self.health(target)
        return DeploymentResult(
            service=self.name,
            ok=health.ok,
            url=target,
            details={"health": health.__dict__},
        )

    def verify_import(self, module_path: str = "xion_relay_chute.py") -> DeploymentResult:
        path = self.repo_root / module_path
        old_path = list(sys.path)
        try:
            sys.path.insert(0, str(self.repo_root))
            if not path.exists():
                return DeploymentResult(service=self.name, ok=False, id=module_path, details={"error": "missing module"})
            namespace: dict[str, Any] = {"__file__": str(path), "__name__": "__xion_ops_chute_verify__"}
            exec(path.read_text(encoding="utf-8"), namespace)
            ok = "chute" in namespace or "stub" in namespace
            return DeploymentResult(
                service=self.name,
                ok=ok,
                id=module_path,
                details={"has_chute": "chute" in namespace, "has_stub": "stub" in namespace},
            )
        except Exception as exc:
            return DeploymentResult(service=self.name, ok=False, id=module_path, details={"error": str(exc)})
        finally:
            sys.path[:] = old_path

    def build_chute_image(self, module_path: str = "xion_relay_chute.py") -> DeploymentResult:
        result = run_command(["chutes", "build", module_path], cwd=self.repo_root, check=False)
        return DeploymentResult(
            service=self.name,
            ok=result.returncode == 0,
            id=module_path,
            details={"stdout": result.stdout, "stderr": result.stderr},
        )

    def deploy_chute(self, module_path: str = "xion_relay_chute.py") -> DeploymentResult:
        result = run_command(["chutes", "deploy", module_path], cwd=self.repo_root, check=False)
        chute_id = _extract_field(result.stdout, "id") or _extract_field(result.stdout, "chute_id")
        url = _extract_url(result.stdout)
        return DeploymentResult(
            service=self.name,
            ok=result.returncode == 0,
            id=chute_id or module_path,
            url=url,
            details={"stdout": result.stdout, "stderr": result.stderr},
        )

    def warmup(self, url: str | None = None) -> DeploymentResult:
        target = url or self.base_url()
        health = self.health(target)
        return DeploymentResult(service=self.name, ok=health.ok, url=target, details=health.details)

    def rollback_chute(self, chute_id: str) -> DeploymentResult:
        result = run_command(["chutes", "chutes", "delete", chute_id], cwd=self.repo_root, check=False)
        return DeploymentResult(
            service=self.name,
            ok=result.returncode == 0,
            id=chute_id,
            details={"stdout": result.stdout, "stderr": result.stderr},
        )

    def base_url(self) -> str:
        return os.environ.get("XION_CHUTES_BASE_URL") or os.environ.get("XION_SECONDARY_HTTPS_BASE", "")


def _extract_url(output: str) -> str | None:
    for token in output.split():
        if token.startswith("https://") or token.startswith("http://"):
            return token.strip().strip(",")
    return None


def _extract_field(output: str, key: str) -> str | None:
    try:
        payload: Any = json.loads(output)
    except json.JSONDecodeError:
        return None
    if isinstance(payload, dict) and isinstance(payload.get(key), str):
        return str(payload[key])
    return None

