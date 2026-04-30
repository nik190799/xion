"""Tests for the credential vault gateway."""

from __future__ import annotations

import pytest

from orchestrator.vault import EnvVault, ThresholdVaultStub, Vault, VaultSettings, get_vault


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

    assert isinstance(vault, ThresholdVaultStub)
    assert isinstance(vault, Vault)
    assert vault.is_sealed() is True
    assert vault.posture() == "sealed-doctrine-only"
    with pytest.raises(NotImplementedError, match="KW-VAULT-001"):
        vault.unlock("XION_CHUTES_API_KEY")


def test_vault_factory_rejects_unknown_provider():
    with pytest.raises(ValueError, match="unsupported XION_VAULT_PROVIDER"):
        get_vault(VaultSettings(provider="hsm-moonbase"))
