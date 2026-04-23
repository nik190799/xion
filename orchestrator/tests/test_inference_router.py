"""Inference Router floor (Invariant 17) — minimal structural tests."""

from __future__ import annotations

import pytest

from orchestrator.inference_router import InferenceRouter, OpenWeightsFloorStub, default_manifest_path


def test_bootstrap_accepts_manifest_matched_stub(tmp_path, monkeypatch):
    m = tmp_path / "m.json"
    m.write_text(
        '{"schema_version":1,"open_weights":[{"id":"x","category":"open_weights_self_hostable",'
        '"format":"sentinel","sentinel_path":"sentinel_open_weights.txt","sha256":"da7807eba9696856c6a2d7971cc9a764e37ebf3eb547d55a8dde9cae54595985"}]}',
        encoding="utf-8",
    )
    r = InferenceRouter(manifest_path=m)
    r.register(OpenWeightsFloorStub(provider_id="x"))
    r.bootstrap()


def test_bootstrap_refuses_without_floor_provider(tmp_path):
    m = tmp_path / "m.json"
    m.write_text('{"schema_version":1,"open_weights":[]}', encoding="utf-8")
    r = InferenceRouter(manifest_path=m)
    with pytest.raises(RuntimeError, match="Invariant 17"):
        r.bootstrap()


def test_default_manifest_path_is_under_inference_router():
    p = default_manifest_path()
    assert p.name == "open_weights_manifest.json"
