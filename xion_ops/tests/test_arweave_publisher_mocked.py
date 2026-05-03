from __future__ import annotations

from xion_ops.services.arweave import ArweaveService


def test_publish_file_without_wallet_returns_dry_run(monkeypatch, tmp_path):
    monkeypatch.delenv("XION_REGISTRY_WALLET_JWK_PATH", raising=False)
    monkeypatch.delenv("ARWEAVE_WALLET_PATH", raising=False)
    path = tmp_path / "artifact.txt"
    path.write_text("xion", encoding="utf-8")

    tx = ArweaveService(repo_root=tmp_path).publish_file(path, {"Xion-Artifact": "test"})

    assert tx.status == "dry-run"
    assert len(tx.id) == 64

