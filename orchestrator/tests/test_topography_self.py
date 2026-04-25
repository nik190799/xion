"""``GET /self`` response shape (Phase 6.4.b / Block N)."""

from __future__ import annotations

import re

import pytest


def test_get_self_topography_lineage_vitals_governance(app_factory) -> None:
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    app = app_factory(tick_cadence_s=0.01)
    with TestClient(app) as client:
        r = client.get("/self")
    assert r.status_code == 200
    data = r.json()
    for k in ("topography", "sensorium", "vitals", "governance", "as_of_utc_ns"):
        assert k in data
    assert re.fullmatch(
        r"[0-9a-f]{64}", str(data["topography"].get("lineage_hash", ""))
    )
    assert len(data["vitals"].get("domains", [])) >= 8
    assert "open_kw_count" in data["governance"]
    assert "api_surface" in data["topography"]
    assert isinstance(data["topography"]["api_surface"], list)
