from __future__ import annotations

import json

from xion_ops.services.akash import AkashService
from xion_ops.types import CommandResult


def test_create_deployment_parses_dseq(monkeypatch, tmp_path):
    monkeypatch.setenv("XION_AKASH_WAIT_TX", "0")
    service = AkashService(repo_root=tmp_path)
    payload = {
        "code": 0,
        "events": [
            {
                "type": "akash.deployment.v1.EventDeploymentCreated",
                "attributes": [
                    {"key": "id", "value": json.dumps({"owner": "akash1x", "dseq": "123"})},
                ],
            }
        ],
    }

    monkeypatch.setattr(
        service,
        "_provider_services",
        lambda *args, **kwargs: CommandResult(tuple(args), 0, json.dumps(payload), ""),
    )

    assert service.create_deployment("relay.yaml") == "123"


def test_providers_sorted_by_total_open_price_lowest_first(tmp_path):
    service = AkashService(repo_root=tmp_path)
    ordered = service._providers_sorted_by_total_open_price(
        [
            {"bid": {"state": "open", "price": {"amount": "2.0"}, "id": {"provider": "p2"}}},
            {"bid": {"state": "open", "price": {"amount": "1.0"}, "id": {"provider": "p1"}}},
        ],
        set(),
    )
    assert ordered == ["p1", "p2"]


def test_providers_sorted_skips_rejected_providers(tmp_path):
    service = AkashService(repo_root=tmp_path)
    ordered = service._providers_sorted_by_total_open_price(
        [
            {"bid": {"state": "open", "price": {"amount": "1.0"}, "id": {"provider": "p1"}}},
            {"bid": {"state": "open", "price": {"amount": "2.0"}, "id": {"provider": "p2"}}},
        ],
        {"p1"},
    )
    assert ordered == ["p2"]


def test_open_orders_for_provider_multi_order(tmp_path):
    service = AkashService(repo_root=tmp_path)
    bids = [
        {"bid": {"state": "open", "price": {"amount": "1"}, "id": {"provider": "p1", "gseq": 1, "oseq": 2}}},
        {"bid": {"state": "open", "price": {"amount": "2"}, "id": {"provider": "p1", "gseq": "1", "oseq": "1"}}},
        {"bid": {"state": "closed", "price": {"amount": "1"}, "id": {"provider": "p1", "gseq": 2, "oseq": 1}}},
    ]
    assert service._open_orders_for_provider(bids, "p1") == [(1, 1), (1, 2)]


def test_gas_tx_flags_use_env(monkeypatch, tmp_path):
    monkeypatch.setenv("AKASH_GAS", "500000")
    monkeypatch.setenv("AKASH_GAS_ADJUSTMENT", "1.5")
    monkeypatch.setenv("AKASH_GAS_PRICES", "0.025uakt")
    service = AkashService(repo_root=tmp_path)
    assert service._gas_tx_flags() == ["--gas", "500000", "--gas-adjustment", "1.5", "--gas-prices", "0.025uakt"]
