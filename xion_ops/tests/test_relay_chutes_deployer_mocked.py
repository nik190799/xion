from __future__ import annotations

import pytest

from xion_ops.deployers.relay_chutes import RelayChutesDeployer
from xion_ops.types import ArTx, DeployContext, DeploymentResult, VerifyReport


def test_relay_chutes_build_failure_skips_deploy(monkeypatch, tmp_path) -> None:
    deployer = RelayChutesDeployer(repo_root=tmp_path)

    monkeypatch.setattr(deployer, "prepare", lambda ctx: None)
    monkeypatch.setattr(deployer.chutes, "rollback_chute", lambda cid: pytest.fail(f"unexpected rollback {cid!r}"))
    monkeypatch.setattr(deployer, "verify", lambda result: VerifyReport(ok=False, command="stub", output=""))

    def boom_build(*_a, **_k):
        return DeploymentResult(service="chutes", ok=False, id="xion_relay_chute:chute", details={"err": True})

    monkeypatch.setattr(deployer.chutes, "build_chute_image", boom_build)

    invoked = []

    def boom_deploy(*args, **kwargs):  # noqa: ARG002
        invoked.append(1)

    monkeypatch.setattr(deployer.chutes, "deploy_chute", boom_deploy)

    record = deployer.run(DeployContext(repo_root=tmp_path, params={"build_wait": True, "publish_registry": False}))
    assert record.result.ok is False
    assert record.result.details.get("build_ok") is False
    assert invoked == []


def test_relay_chutes_rollback_only_when_deploy_chute_fails(monkeypatch, tmp_path) -> None:
    deployer = RelayChutesDeployer(repo_root=tmp_path)

    rollback_ids: list[str] = []

    def capture_rollback(cid: str) -> DeploymentResult:
        rollback_ids.append(cid)
        return DeploymentResult(service="chutes", ok=True, id=cid, details={})

    monkeypatch.setattr(deployer, "prepare", lambda ctx: None)
    monkeypatch.setattr(deployer.chutes, "rollback_chute", capture_rollback)
    monkeypatch.setattr(
        deployer.chutes,
        "deploy_chute",
        lambda *_a, accept_fee=False, **_k: DeploymentResult(
            service="chutes",
            ok=False,
            id="failed-id",
            url=None,
            details={"stdout": "", "stderr": "no"},
        ),
    )

    record = deployer.run(DeployContext(repo_root=tmp_path, params={}))
    assert record.result.ok is False
    assert record.result.details["deploy_command_ok"] is False
    assert rollback_ids == ["failed-id"]


def test_relay_chutes_skip_rollback_when_warmup_fails(monkeypatch, tmp_path) -> None:
    deployer = RelayChutesDeployer(repo_root=tmp_path)

    rollback_ids: list[str] = []

    monkeypatch.setattr(deployer, "prepare", lambda ctx: None)
    monkeypatch.setattr(deployer.chutes, "rollback_chute", lambda cid: rollback_ids.append(cid))
    monkeypatch.setattr(
        deployer.chutes,
        "deploy_chute",
        lambda *_a, accept_fee=False, **_k: DeploymentResult(
            service="chutes",
            ok=True,
            id="keep-me",
            url="https://chute.example/",
            details={"stdout": "ok"},
        ),
    )
    monkeypatch.setattr(
        deployer.chutes,
        "warmup_until_cords_green",
        lambda *a, **k: DeploymentResult(service="chutes", ok=False, url="https://chute.example/", details={"attempts": 3}),
    )

    monkeypatch.setattr(
        deployer.chutes,
        "verify_cords",
        lambda url=None: DeploymentResult(service="chutes", ok=True, url="https://chute.example/", details={}),
    )
    record = deployer.run(DeployContext(repo_root=tmp_path, params={"publish_registry": False}))
    assert record.result.ok is False
    assert record.result.details["deploy_command_ok"] is True
    assert rollback_ids == []


def test_relay_chutes_happy_publish_registry(monkeypatch, tmp_path) -> None:
    deployer = RelayChutesDeployer(repo_root=tmp_path)

    monkeypatch.setattr(deployer, "prepare", lambda ctx: None)

    def no_rollback(cid: str) -> None:
        raise AssertionError("unexpected rollback")

    monkeypatch.setattr(deployer.chutes, "rollback_chute", no_rollback)
    monkeypatch.setattr(
        deployer.chutes,
        "deploy_chute",
        lambda *_a, accept_fee=False, **_k: DeploymentResult(
            service="chutes",
            ok=True,
            id="cid",
            url="https://chute.example/",
            details={"stdout": "deployed"},
        ),
    )
    monkeypatch.setattr(
        deployer.chutes,
        "warmup_until_cords_green",
        lambda *a, **k: DeploymentResult(service="chutes", ok=True, url="https://chute.example/", details={"attempts": 1}),
    )
    monkeypatch.setattr(
        deployer.arweave,
        "publish_relay_registry",
        lambda *args, **kwargs: ArTx(id="relay-tx", status="dry-run"),
    )

    monkeypatch.setattr(deployer, "verify", lambda result: VerifyReport(ok=True, command="stub", output=""))

    record = deployer.run(DeployContext(repo_root=tmp_path, params={}))
    assert record.result.ok is True
    assert record.result.tx == "relay-tx"
    assert record.verify.ok is True

