"""Deployer interface for end-to-end API-service deployments."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import ClassVar

from xion_ops.types import DeployContext, DeploymentRecord, DeploymentResult, VerifyReport, now_iso


class Deployer(ABC):
    """Compose service primitives into one deployable system lifecycle."""

    name: ClassVar[str]

    def __init__(self, *, repo_root: Path | str = ".") -> None:
        self.repo_root = Path(repo_root)

    @abstractmethod
    def prepare(self, ctx: DeployContext) -> None:
        """Run preflight checks before a write is attempted."""

    @abstractmethod
    def deploy(self, ctx: DeployContext) -> DeploymentResult:
        """Execute the deployment write path."""

    @abstractmethod
    def verify(self, result: DeploymentResult) -> VerifyReport:
        """Verify the deployment evidence."""

    @abstractmethod
    def rollback(self, result: DeploymentResult) -> None:
        """Undo recoverable writes when deployment fails."""

    def run(self, ctx: DeployContext) -> DeploymentRecord:
        self.prepare(ctx)
        result = self.deploy(ctx)
        if not result.ok:
            self.rollback(result)
        verify = self.verify(result)
        return self.record(result, verify, ctx)

    def record(self, result: DeploymentResult, verify: VerifyReport, ctx: DeployContext) -> DeploymentRecord:
        record_id = result.id or f"{self.name}-{now_iso().replace(':', '').replace('-', '')}"
        record = DeploymentRecord(
            id=record_id,
            deployer=self.name,
            result=result,
            verify=verify,
            operator=ctx.operator,
            evidence={"params": ctx.params},
        )
        output_dir = ctx.repo_root / "genesis" / "DEPLOYMENT_RECORDS"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / f"{record_id}.json").write_text(
            json.dumps(record.to_dict(), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return record

