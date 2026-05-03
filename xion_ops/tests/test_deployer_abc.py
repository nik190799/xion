from __future__ import annotations

from xion_ops.deployers import ALL_DEPLOYERS
from xion_ops.deployers.base import Deployer


def test_all_deployers_implement_abc():
    assert {"relay-akash", "relay-chutes", "base-contracts"} <= set(ALL_DEPLOYERS)
    for deployer_cls in ALL_DEPLOYERS.values():
        assert issubclass(deployer_cls, Deployer)

