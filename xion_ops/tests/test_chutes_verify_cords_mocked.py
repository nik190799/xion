"""Unit tests for ChutesService.verify_cords (three public cords)."""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from xion_ops.services.chutes import ChutesService
from xion_ops.types import CommandResult, DeploymentResult


@pytest.fixture()
def chutes_svc(tmp_path: Path) -> ChutesService:
    """``verify_cords`` does not touch repo files; shallow root is sufficient."""
    return ChutesService(repo_root=tmp_path)


def _urlopen_cm(status: int, body: bytes = b"{}") -> MagicMock:
    resp = MagicMock()
    resp.status = status
    resp.read.return_value = body
    cm = MagicMock()
    cm.__enter__.return_value = resp
    cm.__exit__.return_value = None
    return cm


def test_verify_cords_ok_when_all_paths_return_200(monkeypatch: pytest.MonkeyPatch, chutes_svc: ChutesService) -> None:
    monkeypatch.delenv("CHUTES_API_KEY", raising=False)
    monkeypatch.delenv("XION_CHUTES_API_KEY", raising=False)
    monkeypatch.setenv("XION_CHUTES_BASE_URL", "https://ex.chutes.ai")
    with patch("xion_ops.services.chutes.urlopen", autospec=True) as mock_urlopen:
        mock_urlopen.return_value = _urlopen_cm(200)
        res = chutes_svc.verify_cords()
    assert res.ok is True
    assert res.details["bearer_attached"] is False
    assert mock_urlopen.call_count == 3
    cords = res.details["cords"]
    assert set(cords) == {"/health", "/quote", "/self"}
    for data in cords.values():
        assert data["ok"] is True
        assert data["status"] == 200


def test_verify_cords_fails_if_quote_non_2xx(monkeypatch: pytest.MonkeyPatch, chutes_svc: ChutesService) -> None:
    monkeypatch.delenv("CHUTES_API_KEY", raising=False)
    monkeypatch.setenv("XION_CHUTES_BASE_URL", "https://ex.chutes.ai")

    cms = [_urlopen_cm(200), _urlopen_cm(401), _urlopen_cm(200)]

    def _next_cm(*_: object, **__: object) -> MagicMock:
        return cms.pop(0)

    with patch("xion_ops.services.chutes.urlopen", side_effect=_next_cm):
        res = chutes_svc.verify_cords()

    assert res.ok is False
    assert res.details["cords"]["/quote"]["ok"] is False
    assert res.details["cords"]["/quote"]["status"] == 401


def test_health_attaches_bearer_when_key_set(monkeypatch: pytest.MonkeyPatch, chutes_svc: ChutesService) -> None:
    monkeypatch.setenv("XION_CHUTES_BASE_URL", "https://ex.chutes.ai")
    monkeypatch.setenv("CHUTES_API_KEY", "sekrit")
    with patch("xion_ops.services.chutes.urlopen", autospec=True) as mock_urlopen:
        mock_urlopen.return_value = _urlopen_cm(200)
        h = chutes_svc.health()

    assert h.ok is True
    req = mock_urlopen.call_args[0][0]
    assert req.get_header("Authorization") == "Bearer sekrit"


def test_warmup_until_cords_green_stops_when_cords_green(monkeypatch: pytest.MonkeyPatch, chutes_svc: ChutesService) -> None:
    monkeypatch.delenv("CHUTES_API_KEY", raising=False)
    monkeypatch.delenv("XION_CHUTES_API_KEY", raising=False)
    monkeypatch.setenv("XION_CHUTES_BASE_URL", "https://ex.chutes.ai")
    monkeypatch.setattr(time, "sleep", lambda _: None)

    rounds = {"n": 0}

    def fv(url=None):
        rounds["n"] += 1
        return DeploymentResult(
            service="chutes",
            ok=rounds["n"] >= 2,
            url="https://ex.chutes.ai",
            details={"cords": {}, "bearer_attached": False, "result": ""},
        )

    monkeypatch.setattr(chutes_svc, "verify_cords", fv)
    res = chutes_svc.warmup_until_cords_green(None, max_wait_seconds=120.0, interval_seconds=1.0)

    assert res.ok is True
    assert rounds["n"] == 2
    assert res.details["attempts"] == 2


def test_warmup_until_cords_green_times_out(monkeypatch: pytest.MonkeyPatch, chutes_svc: ChutesService) -> None:
    monkeypatch.delenv("CHUTES_API_KEY", raising=False)
    monkeypatch.setenv("XION_CHUTES_BASE_URL", "https://ex.chutes.ai")
    monkeypatch.setattr(time, "sleep", lambda _: None)
    monkeypatch.setattr(
        chutes_svc,
        "verify_cords",
        lambda url=None: DeploymentResult(service="chutes", ok=False, url="https://ex.chutes.ai", details={"cords": {}, "bearer_attached": False, "result": ""}),
    )
    res = chutes_svc.warmup_until_cords_green(None, max_wait_seconds=0.0, interval_seconds=15.0)
    assert res.ok is False
    assert res.details.get("attempts") == 1


def test_warmup_until_cords_green_runs_platform_warmup_subprocess(monkeypatch: pytest.MonkeyPatch, chutes_svc: ChutesService) -> None:
    import xion_ops.services.chutes as chutes_mod

    monkeypatch.delenv("CHUTES_API_KEY", raising=False)
    monkeypatch.setenv("XION_CHUTES_BASE_URL", "https://ex.chutes.ai")
    monkeypatch.setattr(chutes_mod.shutil, "which", lambda name: "/fake/bin/chutes" if name == "chutes" else None)

    cmds: list[tuple[str, ...]] = []

    def fake_run(cmd, *, cwd=None, check=False, timeout=None, stdin=None):  # noqa: ARG001
        cmds.append(tuple(cmd))
        return CommandResult(tuple(cmd), 0, "", "")

    monkeypatch.setattr(chutes_mod, "run_command", fake_run)
    monkeypatch.setattr(
        chutes_svc,
        "verify_cords",
        lambda url=None: DeploymentResult(service="chutes", ok=True, url="https://ex.chutes.ai", details={"cords": {}, "bearer_attached": False, "result": ""}),
    )

    res = chutes_svc.warmup_until_cords_green(None, platform_warmup_slug="my-chute-slug")

    assert res.ok is True
    assert cmds and cmds[0][:2] == ("chutes", "warmup")
    assert "my-chute-slug" in cmds[0]
