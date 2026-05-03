from __future__ import annotations

from xion_ops.registry import ALL_SERVICES
from xion_ops.services.base import OpsService


def test_all_services_implement_abc():
    assert {"akash", "arweave", "chutes", "base-evm"} <= set(ALL_SERVICES)
    for service_cls in ALL_SERVICES.values():
        assert issubclass(service_cls, OpsService)

