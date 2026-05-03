from __future__ import annotations

from xion_ops.deployers.relay_akash import RelayAkashDeployer
from xion_ops.types import ArTx, DeployContext, DeploymentResult


def test_relay_akash_deployer_publishes_registry(monkeypatch, tmp_path):
    deployer = RelayAkashDeployer(repo_root=tmp_path)

    monkeypatch.setattr(deployer, "prepare", lambda ctx: None)
    monkeypatch.setattr(
        deployer.akash,
        "deploy_relay",
        lambda *args, **kwargs: DeploymentResult(
            service="akash",
            ok=True,
            id="123",
            dseq="123",
            provider="provider",
            url="https://relay.example",
        ),
    )
    monkeypatch.setattr(
        deployer.arweave,
        "publish_relay_registry",
        lambda *args, **kwargs: ArTx(id="tx123", status="dry-run"),
    )

    record = deployer.run(DeployContext(repo_root=tmp_path))

    assert record.result.ok is True
    assert record.result.tx == "tx123"

