"""Phase 5g-v web-client static-mount tests.

Doctrine anchor: ``docs/04-ARCHITECTURE.md`` § "The Web Client Surface
(Phase 5g-v)" and ``docs/31-WEB-CLIENT.md``.

Three postures exercised:
  1) disabled (Genesis Default): no /app mount, no / redirect.
  2) enabled + valid dist: /app/ serves index.html; assets served;
     bare / redirects to /app/.
  3) enabled + missing dist: create_app raises WebClientConfigError.

The tests construct a tiny fake dist/ directory under tmp_path so they
do not depend on the actual ``clients/web/`` Node build. The structural
contract the mount promises (same-origin serve, base /app/, fail-closed
on bad config) is independent of the SPA's contents.
"""

from __future__ import annotations

from pathlib import Path

import pytest


def _make_fake_dist(tmp_path: Path) -> Path:
    dist = tmp_path / "fake-dist"
    dist.mkdir()
    (dist / "index.html").write_text(
        '<!doctype html><html><head><title>Xion</title></head>'
        '<body><div id="root"></div>'
        '<script type="module" src="/app/assets/fake-bundle.js"></script>'
        "</body></html>",
        encoding="utf-8",
    )
    assets = dist / "assets"
    assets.mkdir()
    (assets / "fake-bundle.js").write_text(
        "// fake bundle — not actually executed in these tests\n",
        encoding="utf-8",
    )
    return dist


def test_web_client_disabled_by_default_serves_neither_app_nor_redirect(app_factory):
    """Genesis Default posture: XION_WEB_CLIENT_ENABLED is false
    (autouse fixture), create_app passes an env-loaded
    WebClientConfig(enabled=False, dist_path=None), and no /app
    routes or / redirect exist.
    """
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    app = app_factory()
    with TestClient(app) as client:
        r_app = client.get("/app/")
        assert r_app.status_code == 404

        # The / route is also unregistered; FastAPI returns 404.
        r_root = client.get("/", follow_redirects=False)
        assert r_root.status_code == 404


def test_web_client_enabled_with_valid_dist_serves_index_and_redirects_root(
    app_factory, tmp_path
):
    """Active posture: the operator has built the SPA and flipped the
    flag. The factory mounts /app/ (serving index.html via
    StaticFiles html=True), serves the asset at /app/assets/*, and
    redirects bare / to /app/.
    """
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from orchestrator.api.web_client import WebClientConfig

    dist = _make_fake_dist(tmp_path)
    app = app_factory(
        web_client_config=WebClientConfig(enabled=True, dist_path=dist),
    )
    with TestClient(app) as client:
        r_index = client.get("/app/")
        assert r_index.status_code == 200
        assert "<title>Xion</title>" in r_index.text
        assert 'id="root"' in r_index.text

        r_asset = client.get("/app/assets/fake-bundle.js")
        assert r_asset.status_code == 200
        assert "fake bundle" in r_asset.text

        r_root = client.get("/", follow_redirects=False)
        assert r_root.status_code == 307
        assert r_root.headers["location"] == "/app/"

        # Admission-gated API routes still work: the web-client mount
        # does not shadow any API route.
        r_health = client.get("/health")
        assert r_health.status_code == 200


def test_web_client_enabled_with_missing_dist_raises_at_create_app(
    app_factory, tmp_path
):
    """Fail-closed posture: the operator set the flag but the dist
    directory does not exist. create_app must raise at construction
    time, NOT at first /app/ GET. This mirrors the BillingConfig and
    AdmissionConfig fail-closed patterns.
    """
    pytest.importorskip("fastapi")
    from orchestrator.api.web_client import WebClientConfig, WebClientConfigError

    missing = tmp_path / "does-not-exist"
    with pytest.raises(WebClientConfigError, match="not a readable directory"):
        WebClientConfig(enabled=True, dist_path=missing)


def test_web_client_enabled_with_dir_lacking_index_raises(app_factory, tmp_path):
    """A directory that exists but has no index.html is also a
    fail-closed condition — the SPA bundle is incomplete.
    """
    pytest.importorskip("fastapi")
    from orchestrator.api.web_client import WebClientConfig, WebClientConfigError

    empty = tmp_path / "empty-dir"
    empty.mkdir()
    with pytest.raises(WebClientConfigError, match="does not contain"):
        WebClientConfig(enabled=True, dist_path=empty)


def test_web_client_env_loader_honours_enabled_flag(monkeypatch, tmp_path):
    """The env loader reads XION_WEB_CLIENT_ENABLED + XION_WEB_CLIENT_DIST_PATH
    and returns a validated config. The autouse fixture clears these
    vars; this test re-sets them explicitly.
    """
    from orchestrator.api.web_client import (
        WebClientConfigError,
        load_web_client_config_from_env,
    )

    dist = _make_fake_dist(tmp_path)

    monkeypatch.setenv("XION_WEB_CLIENT_ENABLED", "true")
    monkeypatch.setenv("XION_WEB_CLIENT_DIST_PATH", str(dist))
    cfg = load_web_client_config_from_env()
    assert cfg.enabled is True
    assert cfg.dist_path == dist.resolve()

    # False flag: the dist path variable is ignored.
    monkeypatch.setenv("XION_WEB_CLIENT_ENABLED", "false")
    cfg_off = load_web_client_config_from_env()
    assert cfg_off.enabled is False
    assert cfg_off.dist_path is None

    # Enabled but path does not exist: the loader returns a config
    # whose __post_init__ raises.
    monkeypatch.setenv("XION_WEB_CLIENT_ENABLED", "true")
    monkeypatch.setenv(
        "XION_WEB_CLIENT_DIST_PATH", str(tmp_path / "does-not-exist")
    )
    with pytest.raises(WebClientConfigError):
        load_web_client_config_from_env()
