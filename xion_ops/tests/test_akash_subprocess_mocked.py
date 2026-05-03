from __future__ import annotations

import json

from xion_ops.services.akash import AkashService
from xion_ops.types import CommandResult


def test_create_deployment_parses_dseq(monkeypatch, tmp_path):
    service = AkashService(repo_root=tmp_path)
    payload = {
        "events": [
            {
                "type": "akash.deployment.v1.EventDeploymentCreated",
                "attributes": [
                    {"key": "id", "value": json.dumps({"owner": "akash1x", "dseq": "123"})},
                ],
            }
        ]
    }

    monkeypatch.setattr(
        service,
        "_provider_services",
        lambda *args, **kwargs: CommandResult(tuple(args), 0, json.dumps(payload), ""),
    )

    assert service.create_deployment("relay.yaml") == "123"


def test_lowest_open_provider(tmp_path):
    service = AkashService(repo_root=tmp_path)
    provider = service._lowest_open_provider(
        [
            {"bid": {"state": "open", "price": {"amount": "2.0"}, "id": {"provider": "p2"}}},
            {"bid": {"state": "open", "price": {"amount": "1.0"}, "id": {"provider": "p1"}}},
        ]
    )
    assert provider == "p1"

