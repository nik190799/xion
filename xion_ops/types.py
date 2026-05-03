"""Shared value types for service and deployer boundaries."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal


BalanceStatus = Literal["ok", "shortfall", "zero", "unknown"]
JobStatus = Literal["pending", "running", "succeeded", "failed"]


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class SecondaryTarget:
    currency: str
    target: float


@dataclass(frozen=True)
class WalletInfo:
    id: str
    address: str
    network: str
    currency: str
    target: float
    purpose: str
    service: str
    secondary: tuple[SecondaryTarget, ...] = ()


@dataclass(frozen=True)
class BalanceReport:
    wallet: WalletInfo
    balance: float | None
    raw_balance: str | None = None
    status: BalanceStatus = "unknown"
    message: str = ""

    @property
    def shortfall(self) -> float | None:
        if self.balance is None:
            return None
        return max(self.wallet.target - self.balance, 0)


@dataclass(frozen=True)
class ServiceHealth:
    service: str
    ok: bool
    message: str = ""
    checked_at: str = field(default_factory=now_iso)
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CommandResult:
    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class ArTx:
    id: str
    status: str = "submitted"
    url: str | None = None
    path: str | None = None


@dataclass(frozen=True)
class LeaseStatus:
    dseq: str
    provider: str
    ready: bool
    forwarded_url: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DeploymentResult:
    service: str
    ok: bool
    id: str | None = None
    url: str | None = None
    tx: str | None = None
    dseq: str | None = None
    provider: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VerifyReport:
    ok: bool
    command: str | None = None
    output: str = ""
    code: int = 0


@dataclass(frozen=True)
class DeployContext:
    repo_root: Path
    operator: str = "local-operator"
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DeploymentRecord:
    id: str
    deployer: str
    result: DeploymentResult
    verify: VerifyReport
    operator: str
    created_at: str = field(default_factory=now_iso)
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class JobRecord:
    id: str
    status: JobStatus
    name: str
    created_at: str
    updated_at: str
    result: dict[str, Any] | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

