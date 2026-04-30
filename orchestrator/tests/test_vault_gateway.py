"""Tests for the credential vault gateway."""

from __future__ import annotations

import json

import pytest

from orchestrator.vault import EnvVault, ThresholdVault, ThresholdVaultStub, Vault, VaultSettings, get_vault

PRIME = 257


def _shares(secret: str, *, count: int = 5) -> list[dict[str, object]]:
    raw = secret.encode("utf-8")
    shares: list[dict[str, object]] = []
    for x in range(1, count + 1):
        y = []
        for index, byte in enumerate(raw):
            a1 = 17 + index
            a2 = 29 + index
            y.append((byte + a1 * x + a2 * x * x) % PRIME)
        shares.append({"x": x, "y": y})
    return shares


def test_env_vault_unlocks_named_env_secret(monkeypatch):
    monkeypatch.setenv("XION_TEST_SECRET", "secret-value")

    vault = get_vault(VaultSettings(provider="env"))

    assert isinstance(vault, EnvVault)
    assert isinstance(vault, Vault)
    assert vault.unlock("XION_TEST_SECRET") == "secret-value"
    assert vault.unlock("MISSING_SECRET") is None
    assert vault.is_sealed() is False


def test_vault_factory_selects_threshold_stub():
    vault = get_vault(VaultSettings(provider="threshold"))

    assert isinstance(vault, ThresholdVault)
    assert isinstance(vault, ThresholdVaultStub)
    assert isinstance(vault, Vault)
    assert vault.is_sealed() is True
    assert vault.posture() == "threshold-sealed"
    with pytest.raises(FileNotFoundError, match="XION_THRESHOLD_VAULT_PATH"):
        vault.unlock("XION_CHUTES_API_KEY")


def test_threshold_vault_unlocks_from_three_shares(tmp_path, monkeypatch):
    bundle = {"threshold": 3, "secrets": {"XION_TEST_SECRET": _shares("secret-value")}}
    path = tmp_path / "threshold-vault.json"
    path.write_text(json.dumps(bundle), encoding="utf-8")
    monkeypatch.setenv("XION_THRESHOLD_VAULT_PATH", str(path))

    vault = get_vault(VaultSettings(provider="threshold"))

    assert vault.is_sealed() is False
    assert vault.posture() == "threshold-local-shamir"
    assert vault.unlock("XION_TEST_SECRET") == "secret-value"
    assert vault.unlock("MISSING_SECRET") is None


def test_vault_factory_rejects_unknown_provider():
    with pytest.raises(ValueError, match="unsupported XION_VAULT_PROVIDER"):
        get_vault(VaultSettings(provider="hsm-moonbase"))
