"""Tests for Base EVM treasury deploy preflight."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from xion_ops.services.base_evm import BaseEvmService


@pytest.fixture
def svc(tmp_path: Path) -> BaseEvmService:
    return BaseEvmService(repo_root=tmp_path)


def test_preflight_sepolia_missing_everything(svc: BaseEvmService) -> None:
    for key in (
        "PRIVATE_KEY",
        "XION_DEPLOYER_PRIVATE_KEY",
        "XION_TREASURY_GOVERNANCE",
        "XION_AO_CORE_AUTHORITY",
        "XION_BRIDGE_CAP_BPS",
    ):
        os.environ.pop(key, None)
    issues = svc.treasury_deploy_preflight_issues("base-sepolia")
    assert len(issues) == 4
    assert any("PRIVATE_KEY" in i for i in issues)
    assert any("XION_TREASURY_GOVERNANCE" in i for i in issues)


def test_preflight_sepolia_ok_with_deployer_synonym(svc: BaseEvmService) -> None:
    os.environ["XION_DEPLOYER_PRIVATE_KEY"] = "0x" + "11" * 32
    os.environ["XION_TREASURY_GOVERNANCE"] = "0x" + "22" * 20
    os.environ["XION_AO_CORE_AUTHORITY"] = "0x" + "33" * 20
    os.environ["XION_BRIDGE_CAP_BPS"] = "1000"
    try:
        assert svc.treasury_deploy_preflight_issues("base-sepolia") == []
    finally:
        for key in (
            "XION_DEPLOYER_PRIVATE_KEY",
            "XION_TREASURY_GOVERNANCE",
            "XION_AO_CORE_AUTHORITY",
            "XION_BRIDGE_CAP_BPS",
        ):
            os.environ.pop(key, None)


def test_preflight_mainnet_requires_constructor_and_rejects_rehearsal_gov(svc: BaseEvmService) -> None:
    for key in (
        "PRIVATE_KEY",
        "XION_DEPLOYER_PRIVATE_KEY",
        "XION_TREASURY_GOVERNANCE",
        "XION_AO_CORE_AUTHORITY",
        "XION_BRIDGE_CAP_BPS",
    ):
        os.environ.pop(key, None)
    issues = svc.treasury_deploy_preflight_issues("base-mainnet")
    assert len(issues) == 4
    os.environ["PRIVATE_KEY"] = "0x" + "11" * 32
    os.environ["XION_TREASURY_GOVERNANCE"] = "0xEBDDDf598b5b53C91ff185501d7b182ae5d6B88A"
    os.environ["XION_AO_CORE_AUTHORITY"] = "0x" + "33" * 20
    os.environ["XION_BRIDGE_CAP_BPS"] = "1000"
    try:
        issues = svc.treasury_deploy_preflight_issues("base-mainnet")
        assert any("rehearsal default" in i for i in issues)
        os.environ["XION_TREASURY_GOVERNANCE"] = "0x" + "22" * 20
        assert svc.treasury_deploy_preflight_issues("base-mainnet") == []
    finally:
        for key in (
            "PRIVATE_KEY",
            "XION_TREASURY_GOVERNANCE",
            "XION_AO_CORE_AUTHORITY",
            "XION_BRIDGE_CAP_BPS",
        ):
            os.environ.pop(key, None)


def test_preflight_unknown_network(svc: BaseEvmService) -> None:
    os.environ["PRIVATE_KEY"] = "0xab"
    try:
        issues = svc.treasury_deploy_preflight_issues("polygon")
        assert any("Unknown network" in i for i in issues)
    finally:
        os.environ.pop("PRIVATE_KEY", None)
