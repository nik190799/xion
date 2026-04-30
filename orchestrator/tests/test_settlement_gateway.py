"""Tests for the settlement-chain gateway."""

from __future__ import annotations

import json

import pytest

from orchestrator.treasury import (
    ArweaveSettlementChain,
    BaseEvmSettlementChain,
    SettlementChain,
    SettlementChainSettings,
    get_settlement_chain,
)


def _write_manifest(root):
    path = root / "genesis"
    path.mkdir()
    (path / "CONTRACT_ADDRESSES.json").write_text(
        json.dumps(
            {
                "status": "testnet",
                "xion_token": "0x" + "1" * 40,
                "imprint": "0x" + "2" * 40,
                "emission_controller": "0x" + "3" * 40,
                "liquidity_lock": "0x" + "4" * 40,
            }
        ),
        encoding="utf-8",
    )


def test_base_evm_settlement_chain_reads_manifest(tmp_path):
    _write_manifest(tmp_path)

    chain = get_settlement_chain(
        SettlementChainSettings(chain="base", repo_root=tmp_path)
    )

    assert isinstance(chain, BaseEvmSettlementChain)
    assert isinstance(chain, SettlementChain)
    assert chain.total_supply() == "0x" + "1" * 40
    assert chain.liquidity_locked() == "0x" + "4" * 40
    assert chain.authorities_root()["imprint"] == "0x" + "2" * 40
    assert chain.egress_window_used() == 0


def test_arweave_settlement_chain_is_real_second_rail(tmp_path):
    (tmp_path / "genesis").mkdir()
    (tmp_path / "genesis" / "TREASURY_VAULTS.json").write_text(
        json.dumps({"arweave_registry_tx": "ar://treasury-registry"}),
        encoding="utf-8",
    )

    chain = get_settlement_chain(SettlementChainSettings(chain="arweave", repo_root=tmp_path))

    assert isinstance(chain, ArweaveSettlementChain)
    assert isinstance(chain, SettlementChain)
    assert chain.total_supply() == "AR:native-supply"
    assert chain.liquidity_locked() == "AR:not-applicable"
    assert chain.authorities_root()["arweave"] == "ar://treasury-registry"
    assert chain.egress_window_used() == 0


def test_settlement_factory_rejects_unknown_chain():
    with pytest.raises(ValueError, match="unsupported XION_SETTLEMENT_CHAIN"):
        get_settlement_chain(SettlementChainSettings(chain="moonbase"))
