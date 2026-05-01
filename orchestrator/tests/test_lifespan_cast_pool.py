from __future__ import annotations

from pathlib import Path

import pytest


def test_lifespan_auto_casts_pool_before_serving(app_factory, monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi.testclient import TestClient

    import orchestrator.api.lifespan as lifespan_module

    calls: list[str] = []

    def fake_cast_pool() -> None:
        calls.append("cast")

    monkeypatch.setattr(lifespan_module, "_ensure_agent_cast_pool_at_boot", fake_cast_pool)
    app = app_factory(cast_pool_on_boot=True)

    with TestClient(app) as client:
        assert client.get("/health").status_code == 200

    assert calls == ["cast"]


def test_lifespan_refuses_boot_when_cast_pool_fails(
    app_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from fastapi.testclient import TestClient

    import orchestrator.api.lifespan as lifespan_module

    def fail_cast_pool() -> None:
        raise RuntimeError("agent-cast failed")

    monkeypatch.setattr(lifespan_module, "_ensure_agent_cast_pool_at_boot", fail_cast_pool)
    app = app_factory(cast_pool_on_boot=True)

    with pytest.raises(RuntimeError, match="agent-cast failed"), TestClient(app):
        pass


def test_cast_pool_seed_then_verify(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import orchestrator.api.lifespan as lifespan_module

    repo = tmp_path
    (repo / "genesis" / "AGENT_SOULS").mkdir(parents=True)
    (repo / "ledgers").mkdir()
    (repo / "genesis" / "HERMES_TOOL_ALLOWLIST.yaml").write_text(
        "hermes_pin:\n  commit: hermes-test\n",
        encoding="utf-8",
    )
    (repo / "genesis" / "AGENT_SOULS" / "worker.yaml").write_text(
        "agent_id: worker\nextends_soul_hash: parent\n",
        encoding="utf-8",
    )
    verified: list[Path] = []
    monkeypatch.setattr(lifespan_module, "_verify_agent_cast_pool", lambda root: verified.append(root))

    lifespan_module._ensure_agent_cast_pool_at_boot(repo)

    ledger = repo / "ledgers" / "AGENT_CAST_LEDGER.jsonl"
    assert ledger.is_file()
    assert '"agent_id":"worker"' in ledger.read_text(encoding="utf-8")
    assert verified == [repo]
