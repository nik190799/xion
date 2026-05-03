from __future__ import annotations

from xion_ops.cli import render_balance_table
from xion_ops.types import BalanceReport, WalletInfo


def test_render_balance_table(capsys):
    wallet = WalletInfo(
        id="sepolia_deployer",
        address="0xabc",
        network="base-sepolia",
        currency="ETH",
        target=0.05,
        purpose="test",
        service="base-evm",
    )

    render_balance_table([BalanceReport(wallet=wallet, balance=0.1, raw_balance="0.1", status="ok")])

    out = capsys.readouterr().out
    assert "service\twallet\tnetwork" in out
    assert "sepolia_deployer" in out
    assert "ok" in out

