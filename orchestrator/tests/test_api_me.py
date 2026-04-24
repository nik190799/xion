"""Tests for GET /me/receipts."""

from fastapi.testclient import TestClient
from orchestrator.api.app import create_app, AppDeps
from unittest.mock import Mock
from pathlib import Path
import json
import pytest

from orchestrator.relay.relay import Relay

@pytest.fixture
def app_deps(tmp_path: Path):
    from orchestrator.api.admission import AdmissionConfig
    
    # Needs a Relay
    relay = Mock(spec=Relay)
    relay.health_snapshot.return_value = Mock(relay_healthy=True, arbiter_healthy=True, watchdog_fires_recent=0, as_of_monotonic_ns=0)
    
    return AppDeps(
        relay=relay,
        tick_cadence_s=0.01,
        sensorium_ledger_path=tmp_path / "SENSORIUM.jsonl",
    )

def test_get_receipts_empty(app_deps, tmp_path):
    # Admission config allows testing
    # XION_API_REQUIRE_BEARER defaults to True. We will pass a token.
    app = create_app(app_deps)
    app.state.anchor_ledger_path = tmp_path / "ANCHOR.jsonl"
    app.state.request_ledger_path = tmp_path / "REQUEST.jsonl"
    app.state.payment_ledger_path = tmp_path / "PAYMENT.jsonl"
    app.state.safety_ledger_path = tmp_path / "SAFETY.jsonl"
    
    # We must patch admission dependency for test
    from orchestrator.api.admission import admission_dependency
    app.dependency_overrides[admission_dependency] = lambda: "test-principal"
    
    client = TestClient(app)
    response = client.get("/me/receipts?since=0")
    assert response.status_code == 200
    assert response.json() == []

def test_get_receipts_with_data(app_deps, tmp_path):
    app = create_app(app_deps)
    anchor_path = tmp_path / "ANCHOR.jsonl"
    req_path = tmp_path / "REQUEST.jsonl"
    
    app.state.anchor_ledger_path = anchor_path
    app.state.request_ledger_path = req_path
    app.state.payment_ledger_path = tmp_path / "PAYMENT.jsonl"
    app.state.safety_ledger_path = tmp_path / "SAFETY.jsonl"
    
    from orchestrator.api.admission import admission_dependency
    app.dependency_overrides[admission_dependency] = lambda: "test-principal"
    
    # Write a source row
    row = {"correlation_id": "c1", "request_arrived_utc_ns": 33000 * 1_000_000_000, "final_outcome": "ok"}
    req_path.write_text(json.dumps(row) + "\n")
    
        # Write anchor
    from orchestrator.anchor.ledger import append
    from orchestrator.anchor.merkle import build_leaf, compute_root
    from orchestrator.api.me import _sha256_canonical

    leaf_hash = build_leaf("c1", "request", _sha256_canonical(row))
    root = compute_root([leaf_hash])
    
    append(
        path=anchor_path,
        period_start_unix=32400,
        period_end_unix=36000,
        ledger_kind="request",
        batch_root_sha256=root,
        batch_size=1,
        leaf_correlation_ids=["c1"]
    )
    
    client = TestClient(app)
    res = client.get("/me/receipts?since=30000")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["correlation_id"] == "c1"
    assert data[0]["ledger_kind"] == "request"
    assert data[0]["batch_root_sha256"] == root
    assert isinstance(data[0]["merkle_proof"], list)
    assert len(data[0]["merkle_proof"]) == 0  # 1 leaf tree has empty proof

    # Filtered
    res_filter = client.get("/me/receipts?since=30000&correlation_id=nonexistent")
    assert res_filter.status_code == 200
    assert len(res_filter.json()) == 0

    res_filter2 = client.get("/me/receipts?since=30000&correlation_id=c1")
    assert res_filter2.status_code == 200
    assert len(res_filter2.json()) == 1
