"""Service interface for load-bearing external operator integrations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import ClassVar

from xion_ops.types import BalanceReport, ServiceHealth, WalletInfo


class OpsService(ABC):
    """Minimum contract every vendor service must expose."""

    name: ClassVar[str]

    def __init__(self, *, repo_root: Path | str = ".") -> None:
        self.repo_root = Path(repo_root)

    @abstractmethod
    def addresses(self) -> list[WalletInfo]:
        """Return all funding targets controlled by this service."""

    @abstractmethod
    def balances(self) -> list[BalanceReport]:
        """Return live balances and target status for this service."""

    @abstractmethod
    def health(self) -> ServiceHealth:
        """Return a best-effort live health probe for the service boundary."""

