"""Central registry for operator services and deployers."""

from __future__ import annotations

from pathlib import Path
from typing import TypeAlias

from xion_ops.services import AkashService, ArweaveService, BaseEvmService, ChutesService
from xion_ops.services.base import OpsService

ServiceFactory: TypeAlias = type[OpsService]

ALL_SERVICES: dict[str, ServiceFactory] = {
    AkashService.name: AkashService,
    ArweaveService.name: ArweaveService,
    ChutesService.name: ChutesService,
    BaseEvmService.name: BaseEvmService,
}


def get_service(name: str, *, repo_root: Path | str = ".") -> OpsService:
    try:
        service_cls = ALL_SERVICES[name]
    except KeyError as exc:
        raise KeyError(f"unknown xion-ops service: {name}") from exc
    return service_cls(repo_root=repo_root)


def service_names() -> list[str]:
    return sorted(ALL_SERVICES)


def get_deployer(name: str, *, repo_root: Path | str = "."):
    from xion_ops.deployers import ALL_DEPLOYERS

    try:
        deployer_cls = ALL_DEPLOYERS[name]
    except KeyError as exc:
        raise KeyError(f"unknown xion-ops deployer: {name}") from exc
    return deployer_cls(repo_root=repo_root)


def deployer_names() -> list[str]:
    from xion_ops.deployers import ALL_DEPLOYERS

    return sorted(ALL_DEPLOYERS)

