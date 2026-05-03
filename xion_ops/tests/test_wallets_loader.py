from __future__ import annotations

import json

from xion_ops.wallets import load_funding_targets


def test_load_funding_targets_round_trip(tmp_path):
    registry = tmp_path / "FUNDING_TARGETS.json"
    registry.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "wallets": [
                    {
                        "id": "w",
                        "address": "0x1",
                        "network": "base-sepolia",
                        "currency": "ETH",
                        "target": 0.05,
                        "purpose": "test",
                        "service": "base-evm",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    wallets = load_funding_targets(registry)

    assert len(wallets) == 1
    assert wallets[0].id == "w"
    assert wallets[0].target == 0.05

