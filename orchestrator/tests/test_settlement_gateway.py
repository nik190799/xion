"""Tests for the settlement-chain gateway."""

from __future__ import annotations

import json

import pytest

from orchestrator.treasury import (
    BaseEvmSettlementChain,
    FutureChainStub,
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


def test_future_chain_stub_does_not_fake_second_rail():
    chain = get_settlement_chain(SettlementChainSettings(chain="future-chain"))

    assert isinstance(chain, FutureChainStub)
    assert isinstance(chain, SettlementChain)
    with pytest.raises(NotImplementedError, match="KW-TREASURY-CHAIN-001"):
        chain.total_supply()


def test_settlement_factory_rejects_unknown_chain():
    with pytest.raises(ValueError, match="unsupported XION_SETTLEMENT_CHAIN"):
        get_settlement_chain(SettlementChainSettings(chain="moonbase"))
