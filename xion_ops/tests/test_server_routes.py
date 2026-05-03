from __future__ import annotations

import os

import pytest


def test_server_health_route(monkeypatch):
    fastapi = pytest.importorskip("fastapi")
    assert fastapi is not None
    from fastapi.testclient import TestClient

    monkeypatch.setenv("XION_OPS_BEARER", "token")
    from xion_ops.server import create_app

    client = TestClient(create_app())
    assert client.get("/health").json() == {"ok": True}
    unauthorized = client.get("/services")
    assert unauthorized.status_code == 401
    authorized = client.get("/services", headers={"Authorization": "Bearer token"})
    assert authorized.status_code == 200
    assert "services" in authorized.json()

    os.environ.pop("XION_OPS_BEARER", None)

