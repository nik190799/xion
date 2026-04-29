"""Tests for the AO Core gateway boundary."""

from __future__ import annotations

import asyncio

import pytest

import orchestrator.ao_core.client as client_module
from orchestrator.ao_core.client import LegacynetAOCoreGateway, LocalnetAOCoreGateway
from orchestrator.ao_core.gateway import (
    AOCoreGateway,
    AOCoreGatewaySettings,
    get_ao_core_gateway,
)


def test_factory_defaults_to_localnet_provider(monkeypatch):
    monkeypatch.delenv("XION_AO_CORE_SUBSTRATE", raising=False)
    monkeypatch.setenv("XION_AO_PROCESS_ID", "proc-1")
    monkeypatch.setenv("XION_AOS_BINARY_PATH", "aos-dev")

    gateway = get_ao_core_gateway()

    assert isinstance(gateway, LocalnetAOCoreGateway)
    assert isinstance(gateway, AOCoreGateway)
    assert gateway.process_id == "proc-1"
    assert gateway.aos_binary_path == "aos-dev"


def test_factory_selects_legacynet_placeholder():
    gateway = get_ao_core_gateway(
        AOCoreGatewaySettings(
            substrate="legacynet",
            process_id="proc-2",
            ao_gateway_url="https://cu.example",
        )
    )

    assert isinstance(gateway, LegacynetAOCoreGateway)
    assert isinstance(gateway, AOCoreGateway)
    assert gateway.ao_gateway_url == "https://cu.example"


def test_factory_rejects_unknown_substrate():
    with pytest.raises(ValueError, match="unsupported XION_AO_CORE_SUBSTRATE"):
        get_ao_core_gateway(AOCoreGatewaySettings(substrate="moonbase"))


def test_localnet_commit_state_invokes_aos(monkeypatch):
    calls = []

    class _Proc:
        returncode = 0

        async def communicate(self):
            return b"message-id", b""

    async def fake_create_subprocess_exec(*args, **kwargs):
        calls.append((args, kwargs))
        return _Proc()

    monkeypatch.setattr(
        client_module.asyncio,
        "create_subprocess_exec",
        fake_create_subprocess_exec,
    )

    gateway = LocalnetAOCoreGateway(process_id="proc-3", aos_binary_path="aos-test")
    ok = asyncio.run(gateway.commit_state(7, "a" * 64, "corr-1"))

    assert ok is True
    args, kwargs = calls[0]
    assert args[:3] == ("aos-test", "proc-3", "--eval")
    assert 'Action = "commit-state"' in args[3]
    assert 'tip_height = "7"' in args[3]
    assert 'state_root_sha256 = "' + ("a" * 64) + '"' in args[3]
    assert 'correlation_id = "corr-1"' in args[3]
    assert kwargs["stdout"] == client_module.asyncio.subprocess.PIPE
    assert kwargs["stderr"] == client_module.asyncio.subprocess.PIPE


def test_localnet_commit_state_failure_returns_false(monkeypatch):
    class _Proc:
        returncode = 1

        async def communicate(self):
            return b"", b"boom"

    async def fake_create_subprocess_exec(*args, **kwargs):
        return _Proc()

    monkeypatch.setattr(
        client_module.asyncio,
        "create_subprocess_exec",
        fake_create_subprocess_exec,
    )

    gateway = LocalnetAOCoreGateway(process_id="proc-4")
    ok = asyncio.run(gateway.commit_state(1, "b" * 64, "corr-2"))

    assert ok is False


def test_legacynet_placeholder_does_not_fake_commit_state():
    gateway = LegacynetAOCoreGateway(process_id="proc-5")

    with pytest.raises(NotImplementedError, match="CU/MU/SU HTTP messaging"):
        asyncio.run(gateway.commit_state(1, "c" * 64, "corr-3"))
